@tool
extends RefCounted
## "Compiles" a CSG brush tree into a lightmap-ready mesh, like qbsp did for Quake maps.
##
## * World-aligned box-projected UVs (Quake-style texture alignment) at the texel density
##   given by res://materials/materials.json ("tile_m": metres per texture repeat), so a CSG
##   level uses exactly the same texel density as the TrenchBroom and Blender levels.
## * Smooth/flat normals from the CSG result, MikkTSpace tangents for normal mapping.
## * A UV2 lightmap unwrap (xatlas) and a trimesh collision shape.

const DEFAULT_TILE := 2.0
const LIGHTMAP_TEXEL_SIZE := 0.1 # metres per lightmap texel (before LightmapGI.texel_scale)


static func _load_tiles() -> Dictionary:
	var f := FileAccess.open("res://materials/materials.json", FileAccess.READ)
	if f == null:
		return {}
	var d = JSON.parse_string(f.get_as_text())
	return d if d is Dictionary else {}


static func _tile_for(mat: Material, tiles: Dictionary) -> float:
	if mat == null:
		return DEFAULT_TILE
	var key := mat.resource_path.get_file().get_basename()
	if tiles.has(key) and tiles[key] is Dictionary:
		return float(tiles[key].get("tile_m", DEFAULT_TILE))
	return DEFAULT_TILE


## World-aligned projection onto the dominant axis plane, oriented so textures read
## upright and unmirrored from inside the room.
static func project_uv(v: Vector3, n: Vector3, tile: float) -> Vector2:
	var a := n.abs()
	var uv: Vector2
	if a.x >= a.y and a.x >= a.z:
		uv = Vector2(-v.z if n.x > 0.0 else v.z, -v.y)
	elif a.y >= a.z:
		uv = Vector2(v.x, v.z if n.y > 0.0 else -v.z)
	else:
		uv = Vector2(v.x if n.z > 0.0 else -v.x, -v.y)
	return uv / tile


static func find_source(root: Node) -> CSGShape3D:
	for n in root.get_tree().get_nodes_in_group("csg_source"):
		if n is CSGShape3D and (n == root or root.is_ancestor_of(n)):
			return n
	return null


## Bakes the scene's CSG source into Geometry/Mesh + Geometry/Collision and saves the
## resources next to the scene. Returns OK on success.
static func bake(root: Node) -> Error:
	var csg := find_source(root)
	if csg == null:
		push_error("[Brushfire] No CSGShape3D in group 'csg_source' in this scene.")
		return ERR_DOES_NOT_EXIST
	var target := root.find_child("Geometry", true, false) as StaticBody3D
	if target == null:
		push_error("[Brushfire] Scene needs a StaticBody3D named 'Geometry' to receive the baked mesh.")
		return ERR_DOES_NOT_EXIST

	var t0 := Time.get_ticks_msec()
	var baked: ArrayMesh = csg.bake_static_mesh()
	if baked == null or baked.get_surface_count() == 0:
		push_error("[Brushfire] CSG produced no geometry (is the CSG root inside the tree?).")
		return ERR_CANT_CREATE

	# The outside of the solid "rock" block is never seen; don't waste lightmap texels on it.
	var hull := AABB()
	var rock := csg.get_node_or_null("Rock") as CSGBox3D
	if rock != null:
		hull = AABB(rock.position - rock.size * 0.5, rock.size)
	var culled := 0

	var tiles := _load_tiles()
	var out := ArrayMesh.new()
	var tris := 0
	for s in baked.get_surface_count():
		var mat := baked.surface_get_material(s)
		var arrays := baked.surface_get_arrays(s)
		var verts: PackedVector3Array = arrays[Mesh.ARRAY_VERTEX]
		var normals: PackedVector3Array = arrays[Mesh.ARRAY_NORMAL]
		var indices := PackedInt32Array()
		if arrays[Mesh.ARRAY_INDEX] != null:
			indices = arrays[Mesh.ARRAY_INDEX]
		var tile := _tile_for(mat, tiles)
		var st := SurfaceTool.new()
		st.begin(Mesh.PRIMITIVE_TRIANGLES)
		var count := indices.size() if indices.size() > 0 else verts.size()
		for i in range(0, count, 3):
			var ids := [i, i + 1, i + 2]
			if indices.size() > 0:
				ids = [indices[i], indices[i + 1], indices[i + 2]]
			var a: Vector3 = verts[ids[0]]
			var b: Vector3 = verts[ids[1]]
			var c: Vector3 = verts[ids[2]]
			if (b - a).cross(c - a).length_squared() < 1e-10:
				continue # sliver triangle from the boolean ops
			# One projection axis per triangle keeps UVs continuous across the face.
			var face_n: Vector3 = (normals[ids[0]] + normals[ids[1]] + normals[ids[2]]).normalized()
			if hull.has_volume() and _on_hull(a, b, c, face_n, hull):
				culled += 1
				continue
			for k in 3:
				var v: Vector3 = verts[ids[k]]
				st.set_normal(normals[ids[k]])
				st.set_uv(project_uv(v, face_n, tile))
				st.add_vertex(v)
			tris += 1
		st.index()
		st.generate_tangents()
		st.set_material(mat)
		st.commit(out)

	var err := out.lightmap_unwrap(Transform3D.IDENTITY, LIGHTMAP_TEXEL_SIZE)
	if err != OK:
		push_warning("[Brushfire] lightmap_unwrap failed: %s" % error_string(err))

	var dir := root.scene_file_path.get_base_dir()
	var base := root.scene_file_path.get_file().get_basename()
	var mesh_path := dir.path_join(base + "_geometry.res")
	var shape_path := dir.path_join(base + "_collision.res")
	out.resource_name = base + "_geometry"
	ResourceSaver.save(out, mesh_path, ResourceSaver.FLAG_COMPRESS)
	var shape := out.create_trimesh_shape()
	ResourceSaver.save(shape, shape_path, ResourceSaver.FLAG_COMPRESS)

	var mi := target.get_node("Mesh") as MeshInstance3D
	var col := target.get_node("Collision") as CollisionShape3D
	mi.mesh = ResourceLoader.load(mesh_path, "", ResourceLoader.CACHE_MODE_REPLACE)
	mi.gi_mode = GeometryInstance3D.GI_MODE_STATIC
	col.shape = ResourceLoader.load(shape_path, "", ResourceLoader.CACHE_MODE_REPLACE)
	print("[Brushfire] CSG baked: %d surfaces, %d triangles (%d exterior culled), lightmap %s in %d ms" % [
		out.get_surface_count(), tris, culled, out.lightmap_size_hint, Time.get_ticks_msec() - t0])
	return OK


## True if the triangle lies on the outside of the rock block's bounding box.
static func _on_hull(a: Vector3, b: Vector3, c: Vector3, n: Vector3, hull: AABB) -> bool:
	const EPS := 0.01
	var lo := hull.position
	var hi := hull.end
	for axis in 3:
		if n[axis] < -0.9 and absf(a[axis] - lo[axis]) < EPS and absf(b[axis] - lo[axis]) < EPS and absf(c[axis] - lo[axis]) < EPS:
			return true
		if n[axis] > 0.9 and absf(a[axis] - hi[axis]) < EPS and absf(b[axis] - hi[axis]) < EPS and absf(c[axis] - hi[axis]) < EPS:
			return true
	return false
