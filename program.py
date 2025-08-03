import sys
import requests
from packaging import version
from PyQt5.QtWidgets import QApplication, QMainWindow, QLabel, QVBoxLayout, QWidget, QMessageBox
from PyQt5.QtCore import QThread, QObject, pyqtSignal, QUrl
from PyQt5.QtGui import QDesktopServices

# --- 設定項目: ご自身の環境に合わせて変更してください ---

# ご自身のGitHubリポジトリを "オーナー名/リポジトリ名" の形式で指定
GITHUB_REPO = "verylowfreq/sample_update_checker_python"  # 例: "PyQt/PyQt"

# アプリケーションの現在のバージョン
CURRENT_VERSION = "0.1.0"

# ----------------------------------------------------


class UpdateChecker(QObject):
    """
    バックグラウンドでアップデートを確認するクラス
    """
    # チェック完了時に送信されるシグナル
    # bool: アップデートの有無
    # str: 最新バージョン名
    # str: リリースページのURL
    finished = pyqtSignal(bool, str, str)

    def __init__(self, repo, current_ver):
        super().__init__()
        self.repo = repo
        self.current_version = current_ver
        self.api_url = f"https://api.github.com/repos/{self.repo}/releases/latest"

    def run(self):
        """
        更新チェック処理を実行
        """
        try:
            response = requests.get(self.api_url, timeout=10)
            response.raise_for_status()  # HTTPエラーがあれば例外を発生

            data = response.json()
            latest_version_str = data['tag_name'].lstrip('v') # 'v1.0.0' -> '1.0.0'
            release_url = data['html_url']

            # 現在のバージョンと最新バージョンを比較
            if version.parse(latest_version_str) > version.parse(self.current_version):
                # アップデートがある場合
                self.finished.emit(True, latest_version_str, release_url)
            else:
                # アップデートがない場合
                self.finished.emit(False, "", "")

        except requests.exceptions.RequestException as e:
            print(f"Error checking for updates: {e}")
            self.finished.emit(False, "", "")
        except (KeyError, IndexError) as e:
            print(f"Error parsing API response: {e}")
            self.finished.emit(False, "", "")


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()

        self.setWindowTitle("Application Update Checker")
        self.setGeometry(100, 100, 400, 200)

        # UIのセットアップ
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout(self.central_widget)

        self.version_label = QLabel(f"現在のバージョン: {CURRENT_VERSION}")
        self.status_label = QLabel("更新を確認中...")
        layout.addWidget(self.version_label)
        layout.addWidget(self.status_label)

        # 更新チェックを開始
        self.check_for_updates()

    def check_for_updates(self):
        """
        更新チェッカーを別スレッドで起動する
        """
        self.thread = QThread()
        self.checker = UpdateChecker(GITHUB_REPO, CURRENT_VERSION)
        self.checker.moveToThread(self.thread)

        # スレッド開始時にchecker.runを実行
        self.thread.started.connect(self.checker.run)
        # checker完了時に結果を処理するメソッドを接続
        self.checker.finished.connect(self.on_update_check_finished)
        # checker完了時にスレッドを終了
        self.checker.finished.connect(self.thread.quit)
        # checkerとスレッドをメモリから解放
        self.checker.finished.connect(self.checker.deleteLater)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def on_update_check_finished(self, update_available, latest_version, release_url):
        """
        更新チェック完了時の処理
        """
        if update_available:
            self.status_label.setText(f"New version available: {latest_version}")
            msg_box = QMessageBox()
            msg_box.setIcon(QMessageBox.Information)
            msg_box.setText(f"新しいバージョン ({latest_version}) が利用可能です。")
            msg_box.setInformativeText("ダウンロードページを開きますか？")
            msg_box.setWindowTitle("Update Available")
            msg_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
            msg_box.setDefaultButton(QMessageBox.Ok)
            
            return_value = msg_box.exec_()

            if return_value == QMessageBox.Ok:
                QDesktopServices.openUrl(QUrl(release_url))
        else:
            self.status_label.setText("You are using the latest version.")


if __name__ == '__main__':
    # GITHUB_REPOが初期値のままの場合に警告を表示
    if GITHUB_REPO == "owner/repository":
         print("警告: GITHUB_REPOの値をあなたのリポジトリ名に変更してください。")
         sys.exit(1)

    app = QApplication(sys.argv)
    main_win = MainWindow()
    main_win.show()
    sys.exit(app.exec_())
