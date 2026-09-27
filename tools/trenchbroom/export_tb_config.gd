# Exports the TrenchBroom game configuration (GameConfig.cfg, Brushfire.fgd, icon.png) without
# needing func_godot's local-config UI. Copy the resulting folder into TrenchBroom's "games" dir.
#   godot --headless --path game -s ../tools/trenchbroom/export_tb_config.gd  (TB_OUT=/abs/out/dir)
extends SceneTree


func _init() -> void:
	var out := OS.get_environment("TB_OUT")
	if out.is_empty():
		out = ProjectSettings.globalize_path("res://").path_join("../tools/trenchbroom/Brushfire").simplify_path()
	DirAccess.make_dir_recursive_absolute(out)
	var cfg = load("res://levels/trenchbroom/brushfire_tb_config.tres")
	var f := FileAccess.open(out.path_join("GameConfig.cfg"), FileAccess.WRITE)
	f.store_string(cfg._build_class_text())
	f.close()
	var img := Image.new()
	img.load_svg_from_string(FileAccess.get_file_as_string("res://icon.svg"), 0.25)
	img.save_png(out.path_join("icon.png"))
	var fgd = cfg.fgd_file.duplicate()
	fgd.generate_model_point_class_models = false
	fgd.do_export_file(fgd.FuncGodotTargetMapEditors.TRENCHBROOM, out)
	print("TrenchBroom config exported to ", out)
	quit()
