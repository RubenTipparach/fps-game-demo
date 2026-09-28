"""Install MPFB 2.0.17 from zip into an isolated Blender user dir and unpack the CC0 system assets
into MPFB's user data dir (what the MPFB 'Load pack from zip' operator does: zip.extractall(LocationService.get_user_data()))."""
import bpy, os, sys, zipfile, addon_utils
NPC = os.environ["NPC"]
print("user extensions dir:", bpy.utils.user_resource('EXTENSIONS'))
for r in bpy.context.preferences.extensions.repos:
    print("repo", r.module, r.directory, r.enabled)
res = bpy.ops.extensions.package_install_files(filepath=os.path.join(NPC, "mpfb-2.0.17.zip"), repo='user_default', enable_on_install=True)
print("install result:", res)
print("enabled?", "bl_ext.user_default.mpfb" in bpy.context.preferences.addons)
user_home = bpy.utils.extension_path_user("bl_ext.user_default.mpfb", create=True)
print("extension_path_user:", user_home)
from bl_ext.user_default.mpfb.services import LocationService, AssetService
data_dir = LocationService.get_user_data()
print("MPFB user data:", data_dir)
LocationService.ensure_relevant_directories_exist()
print("check_asset_pack_zip:", AssetService.check_asset_pack_zip(os.path.join(NPC, "mh_system_assets_cc0.zip")))
with zipfile.ZipFile(os.path.join(NPC, "mh_system_assets_cc0.zip")) as z:
    z.extractall(data_dir)
AssetService.rescan_pack_metadata()
AssetService.update_all_asset_lists()
print("packs:", AssetService.get_pack_names())
print("system assets installed:", AssetService.system_assets_pack_is_installed())
bpy.ops.wm.save_userpref()
