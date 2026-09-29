# Writes the game's input map into project.godot.
# Run: godot --headless --path game -s res://../tools/godot/setup_input.gd  (or an absolute path)
extends SceneTree

func key(code: int) -> InputEventKey:
	var e := InputEventKey.new()
	e.physical_keycode = code
	e.device = -1
	return e

func mouse(button: int) -> InputEventMouseButton:
	var e := InputEventMouseButton.new()
	e.button_index = button
	e.device = -1
	return e

func joy_button(b: int) -> InputEventJoypadButton:
	var e := InputEventJoypadButton.new()
	e.button_index = b
	e.device = -1
	return e

func joy_axis(axis: int, value: float) -> InputEventJoypadMotion:
	var e := InputEventJoypadMotion.new()
	e.axis = axis
	e.axis_value = value
	e.device = -1
	return e

func add(action: String, events: Array, deadzone := 0.2) -> void:
	ProjectSettings.set_setting("input/" + action, {"deadzone": deadzone, "events": events})

func _init() -> void:
	add("move_forward", [key(KEY_W), key(KEY_UP), joy_axis(JOY_AXIS_LEFT_Y, -1.0)])
	add("move_back", [key(KEY_S), key(KEY_DOWN), joy_axis(JOY_AXIS_LEFT_Y, 1.0)])
	add("move_left", [key(KEY_A), key(KEY_LEFT), joy_axis(JOY_AXIS_LEFT_X, -1.0)])
	add("move_right", [key(KEY_D), key(KEY_RIGHT), joy_axis(JOY_AXIS_LEFT_X, 1.0)])
	add("look_left", [joy_axis(JOY_AXIS_RIGHT_X, -1.0)], 0.12)
	add("look_right", [joy_axis(JOY_AXIS_RIGHT_X, 1.0)], 0.12)
	add("look_up", [joy_axis(JOY_AXIS_RIGHT_Y, -1.0)], 0.12)
	add("look_down", [joy_axis(JOY_AXIS_RIGHT_Y, 1.0)], 0.12)
	add("jump", [key(KEY_SPACE), joy_button(JOY_BUTTON_A)])
	add("crouch", [key(KEY_CTRL), key(KEY_C), joy_button(JOY_BUTTON_B)])
	add("sprint", [key(KEY_SHIFT), joy_button(JOY_BUTTON_LEFT_STICK)])
	add("fire", [mouse(MOUSE_BUTTON_LEFT), joy_axis(JOY_AXIS_TRIGGER_RIGHT, 1.0)], 0.3)
	add("reload", [key(KEY_R), joy_button(JOY_BUTTON_X)])
	add("use", [key(KEY_E), joy_button(JOY_BUTTON_RIGHT_SHOULDER)])
	add("weapon_1", [key(KEY_1)])
	add("weapon_2", [key(KEY_2)])
	add("weapon_3", [key(KEY_3)])
	add("weapon_next", [mouse(MOUSE_BUTTON_WHEEL_DOWN), joy_button(JOY_BUTTON_Y)])
	add("weapon_prev", [mouse(MOUSE_BUTTON_WHEEL_UP), joy_button(JOY_BUTTON_LEFT_SHOULDER)])
	add("pause", [key(KEY_ESCAPE), joy_button(JOY_BUTTON_START)])
	add("flashlight", [key(KEY_F), joy_button(JOY_BUTTON_DPAD_UP)])
	# Undercity: the deck, saves, and the ten belt slots on 1 to 0.
	add("deck", [key(KEY_TAB), joy_button(JOY_BUTTON_BACK)])
	add("quicksave", [key(KEY_F5)])
	add("quickload", [key(KEY_F9)])
	for i in range(10):
		add("belt_%d" % (i + 1), [key(KEY_1 + i if i < 9 else KEY_0)])
	ProjectSettings.save()
	print("input map written")
	quit()
