from app.utils.file_names import safe_uuid_filename, sanitize_display_filename


def test_sanitize_display_filename_drops_path_components_and_bad_chars():
    assert sanitize_display_filename("../..\\evil<script>.pdf") == "evil_script_.pdf"


def test_safe_uuid_filename_uses_whitelisted_extension():
    display_name, storage_name = safe_uuid_filename("avatar.exe", {"jpg", "png"}, "jpg")

    assert display_name == "avatar.exe"
    assert storage_name.endswith(".jpg")
    assert "/" not in storage_name
    assert "\\" not in storage_name
