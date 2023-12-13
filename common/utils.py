import os


def create_and_open_file(filepath, mode="w"):
    # ファイルのディレクトリ部分を取得
    directory = os.path.dirname(filepath)

    # ディレクトリが存在しない場合は作成
    if directory and not os.path.exists(directory):
        os.makedirs(directory)

    # ファイルをオープン
    return open(filepath, mode)


def update_env_file(env_file_path, key_to_update, new_value):
    # .envファイルを読み込む
    with open(env_file_path, "r") as file:
        lines = file.readlines()

    # 更新するキーを探し、値を変更する
    updated_lines = []
    key_found = False
    for line in lines:
        if line.startswith(key_to_update + "="):
            updated_lines.append(f"{key_to_update}={new_value}\n")
            key_found = True
        else:
            updated_lines.append(line)

    # キーが存在しない場合は追加
    if not key_found:
        updated_lines.append(f"{key_to_update}={new_value}\n")

    # 変更をファイルに書き戻す
    with open(env_file_path, "w") as file:
        file.writelines(updated_lines)
