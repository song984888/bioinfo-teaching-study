##pip install prompt_toolkit==3.0.50 pygments
import subprocess
import tempfile
from pathlib import Path
from prompt_toolkit import prompt
from prompt_toolkit.shortcuts import confirm


from prompt_toolkit import Application
from prompt_toolkit.buffer import Buffer
from prompt_toolkit.layout.containers import HSplit, VSplit, Window
from prompt_toolkit.layout.controls import BufferControl, FormattedTextControl
from prompt_toolkit.layout.layout import Layout
from prompt_toolkit.lexers import PygmentsLexer
from prompt_toolkit.key_binding import KeyBindings
from prompt_toolkit.styles import Style
from pygments.lexers import PythonLexer


class CodeEditor:
    def __init__(self):
        # 初始化缓冲区
        self.buffer = Buffer()

        # 配置语法高亮
        self.lexer = PygmentsLexer(PythonLexer)

        # 创建界面布局
        self.line_numbers = Window(
            content=FormattedTextControl(self._get_line_numbers),
            width=4,
            style="class:lineno"
        )

        self.editor_area = Window(
            content=BufferControl(
                buffer=self.buffer,
                lexer=self.lexer,
                focusable=True
            )
        )

        # 组合布局组件
        self.root_container = HSplit([
            VSplit([
                self.line_numbers,
                self.editor_area
            ])
        ])

        # 设置键绑定
        self.key_bindings = KeyBindings()
        self._setup_key_bindings()

        # 创建应用实例
        self.app = Application(
            layout=Layout(self.root_container),
            key_bindings=self.key_bindings,
            style=self._get_style(),
            full_screen=False
        )

    def _get_line_numbers(self):
        """动态生成行号"""
        text = self.buffer.text
        line_count = text.count('\n') + 1
        return [("class:lineno", f"{i:3d}\n") for i in range(1, line_count + 1)]

    def _get_style(self):
        """自定义样式"""
        return Style.from_dict({
            "lineno": "#AAAAAA bg:#333333",
            "pygments.comment": "#75715E italic",
            "pygments.keyword": "#F92672 bold",
            "pygments.string": "#E6DB74",
            "pygments.number": "#AE81FF",
            "pygments.operator": "#F92672",
        })

    def _setup_key_bindings(self):
        """配置快捷键"""

        @self.key_bindings.add("c-s")
        def _save(event):
            event.app.exit(result=self.buffer.text)

        @self.key_bindings.add("c-c")
        def _exit(event):
            event.app.exit()

    def run(self):
        """启动编辑器"""
        print("代码编辑器 (Ctrl+S 提交 | Ctrl+C 退出)")
        return self.app.run()

    def run(self):
        """运行编辑器并处理调试流程"""
        print("代码编辑器 (Ctrl+S 提交 | Ctrl+C 退出)")
        code = self.app.run()

        if code is not None:
            while True:
                # 调试验证流程
                if self.debug_code(code):
                    if confirm("是否确认提交代码？ (y/n) "):
                        return self.submit_code(code)
                    else:
                        print("提交已取消")
                        return None
                else:
                    retry = confirm("调试失败，是否重新调试？ (y/n) ")
                    if not retry:
                        return None

    def debug_code(self, code):
        """执行代码调试流程"""
        print("\n=== 进入调试模式 ===")
        print("请输入测试输入（输入空白行结束输入）：")

        # 获取用户输入
        test_input = self._get_multiline_input()

        try:
            # 创建临时文件
            with tempfile.TemporaryDirectory() as tmp_dir:
                code_path = Path(tmp_dir) / "debug_code.py"

                # 写入代码文件
                with code_path.open("w", encoding="utf-8") as f:
                    f.write(code)

                # 执行代码
                result = subprocess.run(
                    ["python", str(code_path)],
                    input=test_input,
                    text=True,
                    capture_output=True,
                    timeout=10  # 设置超时时间
                )

                # 显示执行结果
                print("\n=== 执行结果 ===")
                if result.stdout:
                    print("标准输出：\n" + result.stdout)
                if result.stderr:
                    print("错误输出：\n" + result.stderr)

                return result.returncode == 0

        except subprocess.TimeoutExpired:
            print("执行超时，可能存在无限循环")
            return False
        except Exception as e:
            print(f"执行异常：{str(e)}")
            return False

    def _get_multiline_input(self):
        """获取多行测试输入"""
        lines = []
        while True:
            line = prompt(">>> ")
            if not line:
                break
            lines.append(line)
        return "\n".join(lines)

    def submit_code(self, code):
        """提交代码到数据库（示例）"""
        # 这里可以添加数据库存储逻辑
        print("\n=== 代码提交成功 ===")
        print(format_code_with_line_numbers(code))
        return code



def select_language():
    """选择编程语言"""
    print("\n请选择编程语言：")
    for idx, lang in enumerate(LANGUAGE_CONFIG.keys(), 1):
        print(f"{idx}. {lang.upper()}")

    while True:
        choice = input("请输入编号：").strip()
        try:
            index = int(choice) - 1
            language = list(LANGUAGE_CONFIG.keys())[index]
            return language
        except (ValueError, IndexError):
            print("无效输入，请重新选择")


def main_loop():
    """主控制循环"""
    language = select_language()
    current_code = ""

    while True:
        # 进入代码编辑器
        editor = CodeEditor(initial_code=current_code, language=language)
        print(f"\n{language.upper()}代码编辑器（Ctrl+S 提交 | Ctrl+C 退出）")
        code = editor.run()

        if code is None:
            if confirm("确认退出系统吗？"):
                print("系统退出")
                return
            continue

        # 调试循环
        while True:
            debug_success = Debugger.debug_code(code, language)

            if debug_success:
                if confirm("调试成功，是否确认提交？"):
                    print("\n=== 代码提交成功 ===")
                    print(format_code_with_line_numbers(code))
                    return
                else:
                    current_code = code  # 保留当前代码继续编辑
                    break
            else:
                choice = prompt("请选择: [R]重试调试/[E]继续编辑/[Q]放弃提交: ").lower()

                if choice == 'r':
                    continue  # 重新调试当前代码
                elif choice == 'e':
                    current_code = code  # 保留当前代码返回编辑
                    break
                elif choice == 'q':
                    if confirm("确认放弃当前代码吗？"):
                        return
                else:
                    print("无效输入，请重新选择")





def format_code_with_line_numbers(code):
    """为代码添加行号格式化"""
    if not code:
        return ""
    lines = code.split("\n")
    return "\n".join(
        [f"{i:3d} | {line}" for i, line in enumerate(lines, start=1)]
    )

if __name__ == "__main__":
    editor = CodeEditor()
    final_code = editor.run()

    if final_code:
        print("\n最终提交的代码：")
        print(final_code)
    else:
        print("\n未提交任何代码")