from pathlib import Path
from textwrap import wrap

from PIL import Image, ImageDraw, ImageFont


ROOT = Path(__file__).resolve().parents[1]
OUT_DIR = ROOT / "overview" / "outputs"
FONT_REGULAR = "C:/Windows/Fonts/malgun.ttf"
FONT_BOLD = "C:/Windows/Fonts/malgunbd.ttf"


def font(size, bold=False):
    return ImageFont.truetype(FONT_BOLD if bold else FONT_REGULAR, size)


def rounded(draw, box, radius, fill, outline=None, width=1):
    draw.rounded_rectangle(box, radius=radius, fill=fill, outline=outline, width=width)


def text_center(draw, box, text, fnt, fill="#162033", spacing=6):
    x0, y0, x1, y1 = box
    lines = text.split("\n")
    heights = [draw.textbbox((0, 0), line, font=fnt)[3] for line in lines]
    total = sum(heights) + spacing * (len(lines) - 1)
    y = y0 + (y1 - y0 - total) / 2
    for line, h in zip(lines, heights):
        bbox = draw.textbbox((0, 0), line, font=fnt)
        x = x0 + (x1 - x0 - (bbox[2] - bbox[0])) / 2
        draw.text((x, y), line, font=fnt, fill=fill)
        y += h + spacing


def draw_arrow(draw, start, end, color="#64748b", width=8):
    x0, y0 = start
    x1, y1 = end
    draw.line((x0, y0, x1, y1), fill=color, width=width)
    head = 24
    draw.polygon(
        [(x1, y1), (x1 - head, y1 - head * 0.62), (x1 - head, y1 + head * 0.62)],
        fill=color,
    )


def draw_pill(draw, x, y, w, h, label, fill, outline="#cbd5e1"):
    rounded(draw, (x, y, x + w, y + h), h // 2, fill, outline=outline, width=2)
    text_center(draw, (x, y, x + w, y + h), label, font(36, True), fill="#102033")


def draw_source_tile(draw, x, y, w, h, title, subtitle, color):
    rounded(draw, (x, y, x + w, y + h), 22, "#ffffff", outline="#cbd5e1", width=3)
    draw.rectangle((x, y, x + w, y + 10), fill=color)
    draw.text((x + 30, y + 28), title, font=font(36, True), fill="#111827")
    wrapped = "\n".join(wrap(subtitle, width=17))
    draw.multiline_text((x + 30, y + 86), wrapped, font=font(27), fill="#475569", spacing=8)


def draw_analysis_box(draw, x, y, w, h, title, subtitle, fill, outline):
    rounded(draw, (x, y, x + w, y + h), 24, fill, outline=outline, width=3)
    draw.text((x + 34, y + 28), title, font=font(40, True), fill="#111827")
    draw.multiline_text((x + 34, y + 88), subtitle, font=font(30), fill="#334155", spacing=10)


def make_strip():
    img = Image.new("RGB", (4800, 1050), "#f8fafc")
    draw = ImageDraw.Draw(img)

    draw.text((110, 70), "PM 후 유기재료 증착챔버 RGA 자동 연계분석", font=font(64, True), fill="#0f172a")
    draw.text(
        (112, 152),
        "629개 챔버 | 진공 안정화 구간 | PWR + RGA 1~200 AMU + Calibration | 통계 이상진단 + AI 이상진단 | Auto-email",
        font=font(34),
        fill="#475569",
    )

    y = 285
    tile_w, tile_h = 520, 250
    gap = 46
    x0 = 110
    colors = ["#0ea5e9", "#22c55e", "#f59e0b", "#a855f7"]
    sources = [
        ("1 PM 스케줄", "챔버별 PM 완료 및 재가동 타이밍 확인", colors[0]),
        ("2 FDC PWR", "crucible power on 후 outgassing 구간 식별", colors[1]),
        ("3 RGA 1~200", "AMU별 시계열 gas signature 수집", colors[2]),
        ("4 RGA Cal.", "주기 캘리브레이션 이력과 신뢰도 보정", colors[3]),
    ]
    for i, item in enumerate(sources):
        x = x0 + i * (tile_w + gap)
        draw_source_tile(draw, x, y, tile_w, tile_h, *item)
        if i < len(sources) - 1:
            draw_arrow(draw, (x + tile_w + 6, y + tile_h // 2), (x + tile_w + gap - 14, y + tile_h // 2))

    mid_x = x0 + 4 * (tile_w + gap) + 26
    draw_arrow(draw, (x0 + 4 * (tile_w + gap) - gap + tile_w + 8, y + tile_h // 2), (mid_x - 34, y + tile_h // 2))
    draw_analysis_box(
        draw,
        mid_x,
        y - 2,
        620,
        tile_h + 4,
        "DB 추출·전처리",
        "챔버별 데이터 자동 조회\n시간축 정렬 / 결측·노이즈 처리",
        "#eff6ff",
        "#93c5fd",
    )
    draw_arrow(draw, (mid_x + 630, y + tile_h // 2), (mid_x + 725, y + tile_h // 2))
    draw_analysis_box(
        draw,
        mid_x + 750,
        y - 2,
        700,
        tile_h + 4,
        "연계분석·이상진단",
        "유의차 통계 분석\nAI 패턴 이상 탐지 / 원인 후보",
        "#f0fdf4",
        "#86efac",
    )
    draw_arrow(draw, (mid_x + 1460, y + tile_h // 2), (mid_x + 1555, y + tile_h // 2))
    draw_analysis_box(
        draw,
        mid_x + 1580,
        y - 2,
        560,
        tile_h + 4,
        "Auto-email",
        "챔버별 요약 리포트\n알람 / 첨부 / 담당자 발송",
        "#fff7ed",
        "#fdba74",
    )

    draw_pill(draw, 220, 665, 1250, 88, "수작업 FDC 조회·개별 가공 → 자동 추출·전처리·진단·보고", "#e0f2fe", "#7dd3fc")
    draw_pill(draw, 1580, 665, 980, 88, "과도 outgassing 직후 안정화 시간 구간만 분석", "#dcfce7", "#86efac")
    draw_pill(draw, 2670, 665, 900, 88, "통계 기준 + AI 기준을 병렬 비교", "#fef3c7", "#fbbf24")

    draw.text((112, 840), "Output", font=font(33, True), fill="#334155")
    draw.line((250, 858, 4550, 858), fill="#cbd5e1", width=3)
    draw.text(
        (112, 902),
        "챔버별 RGA AMU 이상 peak, baseline drift, calibration 영향, PWR 연동 outgassing 패턴을 자동 리포트로 발송",
        font=font(38, True),
        fill="#0f172a",
    )

    path = OUT_DIR / "rga_pm_auto_analysis_word_strip.png"
    img.save(path, dpi=(300, 300), quality=95)
    return path


def make_compact():
    img = Image.new("RGB", (3600, 1800), "#f8fafc")
    draw = ImageDraw.Draw(img)
    draw.text((120, 105), "RGA 자동 연계분석 Flow", font=font(76, True), fill="#0f172a")
    draw.text((124, 198), "629개 증착챔버 · PM 후 진공 안정화 구간 · Auto-email 리포트", font=font(39), fill="#475569")

    steps = [
        ("PM 스케줄", "PM 완료/재가동\n대상 챔버 확정", "#0ea5e9"),
        ("FDC PWR", "crucible power\noutgassing 구간", "#22c55e"),
        ("RGA 1~200", "AMU별 시계열\nsignature 수집", "#f59e0b"),
        ("Calibration", "RGA 주기 보정\n신뢰도 반영", "#a855f7"),
    ]
    x, y = 120, 360
    w, h = 760, 270
    for i, (title, sub, color) in enumerate(steps):
        yy = y + i * 315
        draw_source_tile(draw, x, yy, w, h, title, sub, color)
        draw_arrow(draw, (x + w + 20, yy + h // 2), (x + w + 210, yy + h // 2), width=10)

    draw_analysis_box(draw, 1110, 520, 760, 360, "DB 추출·전처리", "챔버별 자동 조회\n시간축 정렬\n결측·노이즈 처리", "#eff6ff", "#93c5fd")
    draw_arrow(draw, (1885, 700), (2105, 700), width=10)
    draw_analysis_box(draw, 2130, 430, 820, 540, "연계분석", "PWR-RGA 상관 분석\nAMU별 유의차 산출\ncalibration 영향 보정\nbaseline drift 확인", "#f0fdf4", "#86efac")
    draw_arrow(draw, (2540, 990), (2540, 1160), width=10)
    draw_analysis_box(draw, 2130, 1185, 820, 360, "이상진단", "통계치 이상진단\nAI 패턴 이상진단\n원인 후보 ranking", "#fff7ed", "#fdba74")
    draw_arrow(draw, (2965, 1360), (3090, 1360), width=10)
    draw_analysis_box(draw, 3120, 1185, 400, 360, "Auto-email", "요약 리포트\n알람\n첨부 발송", "#fef2f2", "#fca5a5")

    path = OUT_DIR / "rga_pm_auto_analysis_word_compact.png"
    img.save(path, dpi=(300, 300), quality=95)
    return path


def main():
    OUT_DIR.mkdir(parents=True, exist_ok=True)
    for path in (make_strip(), make_compact()):
        print(path)


if __name__ == "__main__":
    main()
