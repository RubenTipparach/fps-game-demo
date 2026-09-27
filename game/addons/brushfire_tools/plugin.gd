@tool
extends EditorPlugin
## Brushfire level pipeline, available under Project > Tools:
##   Brushfire: Bake CSG Level         - compile CSG brushes into a UV-mapped, UV2-unwrapped mesh
##   Brushfire: Build func_godot Maps  - (re)build TrenchBroom .map geometry with lightmap UV2
##   Brushfire: Bake Navigation        - bake the NavigationRegion3D navmesh used by enemies
##   Brushfire: Bake Lightmaps         - bake LightmapGI (lightmaps + light probes)
##   Brushfire: Full Rebuild           - all of the above, in order, then save
##
## Batch mode (used to bake the shipped levels headlessly under Xvfb):
##   BRUSHFIRE_BATCH="res://a.tscn:csg,nav,lightmap;res://b.tscn:map,nav,lightmap" godot --editor --path game
## A sectorized level (one LightmapGI per sector) bakes one .lmbake per sector, named after the
## sector node; "lightmap@<sector>" bakes just the sectors whose name contains <sector>.

const BakeCSG := preload("res://addons/brushfire_tools/bake_csg.gd")

const MENU := {
	"Brushfire: Bake CSG Level": ["csg"],
	"Brushfire: Build func_godot Maps": ["map"],
	"Brushfire: Bake Navigation": ["nav"],
	"Brushfire: Bake Lightmaps": ["lightmap"],
	"Brushfire: Full Rebuild (CSG/Map + Nav + Lightmaps)": ["csg", "map", "nav", "lightmap"],
}


func _enter_tree() -> void:
	for label in MENU:
		add_tool_menu_item(label, _run_on_current.bind(MENU[label]))
	var batch := OS.get_environment("BRUSHFIRE_BATCH")
	if not batch.is_empty():
		_run_batch.call_deferred(batch)


func _exit_tree() -> void:
	for label in MENU:
		remove_tool_menu_item(label)


func _run_on_current(steps: Array) -> void:
	var root := EditorInterface.get_edited_scene_root()
	if root == null:
		push_error("[Brushfire] Open a level scene first.")
		return
	await _run_steps(root, steps)
	EditorInterface.save_scene()


func _run_batch(batch: String) -> void:
	# Let the editor finish its first scan/import.
	for i in 30:
		await get_tree().process_frame
	while EditorInterface.get_resource_filesystem().is_scanning():
		await get_tree().process_frame
	for job in batch.split(";", false):
		# "res://x.tscn:csg,nav" -> split at the last ':'
		var sep := job.rfind(":")
		var path := job.substr(0, sep)
		var steps := job.substr(sep + 1).split(",", false)
		print("[Brushfire] === %s : %s" % [path, ", ".join(steps)])
		EditorInterface.open_scene_from_path(path)
		for i in 10:
			await get_tree().process_frame
		var root := EditorInterface.get_edited_scene_root()
		await _run_steps(root, Array(steps))
		EditorInterface.save_scene()
		for i in 5:
			await get_tree().process_frame
	print("[Brushfire] batch finished")
	get_tree().quit()


func _run_steps(root: Node, steps: Array) -> void:
	for step in steps:
		match step:
			"csg":
				if BakeCSG.find_source(root) != null:
					BakeCSG.bake(root)
			"map":
				_build_maps(root)
			"nav":
				await get_tree().process_frame
				_bake_navigation(root)
			"lightmap":
				await _bake_lightmaps(root)
			_ when str(step).begins_with("lightmap@"):
				await _bake_lightmaps(root, str(step).trim_prefix("lightmap@"))


func _build_maps(root: Node) -> void:
	for map in root.find_children("*", "", true, false):
		if not map.has_method("build") or not map.get_script() or map.get_script().get_global_name() != &"FuncGodotMap":
			continue
		var t0 := Time.get_ticks_msec()
		# Unwrap UV2 so the map can be lightmapped.
		map.build_flags = map.build_flags | 1
		map.build()
		_set_owner_recursive(map, root)
		_externalize_meshes(map, root)
		print("[Brushfire] built map %s in %d ms" % [map.name, Time.get_ticks_msec() - t0])


## Save the generated brush meshes as binary .res files next to the scene instead of embedding
## them as text in the .tscn (keeps the scene small and diffs readable).
func _externalize_meshes(map: Node, root: Node) -> void:
	var base := root.scene_file_path.get_basename()
	var i := 0
	for mi in map.find_children("*", "MeshInstance3D", true, false):
		if mi.owner != root or mi.mesh == null or mi.mesh.resource_path.begins_with("res://") and not mi.mesh.resource_path.contains("::"):
			continue
		var path := "%s_mesh_%s.res" % [base, mi.get_parent().name.to_snake_case()]
		ResourceSaver.save(mi.mesh, path, ResourceSaver.FLAG_COMPRESS)
		mi.mesh = ResourceLoader.load(path, "", ResourceLoader.CACHE_MODE_REPLACE)
		i += 1
	print("[Brushfire] saved %d brush meshes next to the scene" % i)


func _set_owner_recursive(node: Node, owner: Node) -> void:
	for c in node.get_children():
		if c.owner == null or c.owner == node:
			c.owner = owner
		# Don't descend into instanced scenes (their children belong to them).
		if c.scene_file_path.is_empty():
			_set_owner_recursive(c, owner)


func _bake_navigation(root: Node) -> void:
	for region in root.find_children("*", "NavigationRegion3D", true, false):
		var t0 := Time.get_ticks_msec()
		region.bake_navigation_mesh(false)
		var nm: NavigationMesh = region.navigation_mesh
		var path := root.scene_file_path.get_basename() + "_navmesh.res"
		ResourceSaver.save(nm, path, ResourceSaver.FLAG_COMPRESS)
		region.navigation_mesh = ResourceLoader.load(path, "", ResourceLoader.CACHE_MODE_REPLACE)
		print("[Brushfire] navmesh %s: %d polygons in %d ms" % [region.name, nm.get_polygon_count(), Time.get_ticks_msec() - t0])


func _find_button(n: Node, text: String) -> Button:
	if n is Button and (n as Button).text == text:
		return n
	for c in n.get_children(true):
		var r := _find_button(c, text)
		if r:
			return r
	return null


func _bake_lightmaps(root: Node, only := "") -> void:
	var all := root.find_children("*", "LightmapGI", true, false)
	for lm in all:
		var sector := String(lm.get_parent().name) if lm.get_parent() != root else String(lm.name)
		if only != "" and not sector.to_lower().contains(only.to_lower()):
			continue
		# Give the bake a destination file next to the scene so no save dialog pops up; one file
		# per LightmapGI when the level has several (one per sector).
		var suffix := "" if all.size() == 1 else "_" + sector.to_snake_case()
		var data_path := root.scene_file_path.get_basename() + suffix + ".lmbake"
		if lm.light_data == null or lm.light_data.resource_path != data_path:
			var data := LightmapGIData.new()
			ResourceSaver.save(data, data_path)
			lm.light_data = ResourceLoader.load(data_path, "", ResourceLoader.CACHE_MODE_REPLACE)
		EditorInterface.get_selection().clear()
		EditorInterface.get_selection().add_node(lm)
		EditorInterface.edit_node(lm)
		for i in 5:
			await get_tree().process_frame
		var button := _find_button(EditorInterface.get_base_control(), "Bake Lightmaps")
		if button == null:
			push_error("[Brushfire] Couldn't find the Bake Lightmaps button; select the LightmapGI node and bake manually.")
			return
		var t0 := Time.get_ticks_msec()
		button.pressed.emit()
		print("[Brushfire] lightmaps baked for %s / %s in %d s" % [root.name, sector, (Time.get_ticks_msec() - t0) / 1000])
