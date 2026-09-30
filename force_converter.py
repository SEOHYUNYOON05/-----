import math
import tkinter as tk
from tkinter import ttk

def convert_force():
    """입력된 힘 값을 변환하여 결과 레이블에 누적하여 표시합니다."""
    value_str = entry_value.get().strip()
    unit = combo_unit.get()
    
    if not value_str:
        lbl_result.config(text=lbl_result.cget("text") + "\n\n⚠️ 값을 입력해주세요.", fg="red")
        return
        
    try:
        val = float(value_str)
        if not math.isfinite(val) or val < 0:
            lbl_result.config(text=lbl_result.cget("text") + "\n\n⚠️ 힘은 유한한 0 이상의 숫자여야 합니다.", fg="red")
            return

        # 기준 단위(kN)로 환산
        if unit == "kN":
            kn = val
        elif unit == "N":
            kn = val / 1000.0
        elif unit == "kgf":
            kn = val / 101.971621

        # 각 단위별 값 계산
        n = kn * 1000.0
        kgf = kn * 101.971621

        # 결과 텍스트 생성
        new_result = (
            f"\n------------------------------\n"
            f"• 입력: {val} {unit}\n"
            f"  └ N   : {n:,.2f} N\n"
            f"  └ kN  : {kn:,.4f} kN\n"
            f"  └ kgf : {kgf:,.2f} kgf"
        )
        
        # 안내 문구만 있는 상태라면 초기화 후 누적 시작
        current_text = lbl_result.cget("text")
        if "값을 입력하고" in current_text:
            current_text = "[ 변환 기록 ]"
            
        lbl_result.config(text=current_text + new_result, fg="blue")
        
    except ValueError:
        lbl_result.config(text=lbl_result.cget("text") + "\n\n⚠️ 잘못된 입력입니다. 숫자를 입력해주세요.", fg="red")

def reset_fields():
    """입력창과 결과 레이블을 초기화합니다."""
    entry_value.delete(0, tk.END)
    combo_unit.current(0)  # 기본값 kN으로 설정
    lbl_result.config(text="값을 입력하고 변환 버튼을 누르세요.", fg="black")

# 메인 창 생성
root = tk.Tk()
root.title("힘 단위 변환기 (Force Converter)")
root.geometry("400x450")  # 누적 출력을 위해 창 세로 길이를 늘림
root.resizable(True, True)  # 스크롤이나 내용 확인을 위해 창 크기 조절 허용

# 1. 입력 프레임
frame_input = tk.Frame(root)
frame_input.pack(pady=15)

lbl_input = tk.Label(frame_input, text="힘 입력: ", font=("Arial", 10))
lbl_input.pack(side=tk.LEFT, padx=5)

entry_value = tk.Entry(frame_input, width=12, font=("Arial", 10))
entry_value.pack(side=tk.LEFT, padx=5)
entry_value.focus()

combo_unit = ttk.Combobox(frame_input, values=["kN", "N", "kgf"], width=6, state="readonly", font=("Arial", 10))
combo_unit.current(0)
combo_unit.pack(side=tk.LEFT, padx=5)

# 2. 버튼 프레임
frame_btn = tk.Frame(root)
frame_btn.pack(pady=10)

btn_convert = tk.Button(frame_btn, text="변환", width=10, command=convert_force, bg="#4CAF50", fg="white", font=("Arial", 10, "bold"))
btn_convert.pack(side=tk.LEFT, padx=5)

btn_reset = tk.Button(frame_btn, text="초기화", width=10, command=reset_fields, bg="#f44336", fg="white", font=("Arial", 10, "bold"))
btn_reset.pack(side=tk.LEFT, padx=5)

root.bind('<Return>', lambda event: convert_force())

# 3. 결과 표시 (ScrolledText나 스크롤이 없는 기본 Label 형태)
lbl_result = tk.Label(root, text="값을 입력하고 변환 버튼을 누르세요.", font=("Arial", 10), justify=tk.LEFT, anchor="n", pady=10)
lbl_result.pack(fill=tk.BOTH, expand=True, padx=20, pady=10)

# GUI 실행
root.mainloop()
