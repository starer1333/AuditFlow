import subprocess
import sys

steps = [
    ["python", "format_and_clean.py"],
    ["python", "ocr_extract.py"],
    ["python", "validate_and_map.py"],
    ["python", "generate_report.py"],
]

for step in steps:
    print(f"\n{'='*40}\n执行: {' '.join(step)}\n{'='*40}")
    result = subprocess.run(step, cwd="D:/桌面/AuditMind")
    if result.returncode != 0:
        print(f"❌ 步骤失败: {' '.join(step)}")
        sys.exit(1)
print("\n🎉 全流程执行成功！请查看 outputs 文件夹。")