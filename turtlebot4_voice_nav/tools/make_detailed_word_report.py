"""Build an editable Vietnamese Word report from existing implementation/evidence.

No navigation or microphone recording is performed by this document generator.
"""
from datetime import datetime, timezone
from pathlib import Path
import json
import math
import re

import numpy as np
from PIL import Image, ImageDraw, ImageFont
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt

from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Cm, Pt, RGBColor
from docx.oxml import OxmlElement
from docx.oxml.ns import qn

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT/'docs'
FIGURES = DOCS/'word_figures'
BLUE = '246B99'
NAVY = '20374D'


def read(relative):
    return json.loads((ROOT/relative).read_text(encoding='utf-8'))


def metrics():
    data = read('artifacts/integration_results.json')
    rows, sent = [], None
    for event in data['statuses']:
        if event.get('event') == 'GOAL_SENT':
            sent = event
        elif event.get('event') == 'GOAL_SUCCEEDED' and sent:
            rows.append(dict(region=event['region_id'], duration_s=event['wall_time']-sent['wall_time'],
                             start=sent.get('pose'), finish=event.get('pose'), error_m=event['error_m'],
                             command=event['command']))
    errors = np.array([row['error_m'] for row in rows])
    result = dict(goals=rows, mean_error_m=float(errors.mean()), median_error_m=float(np.median(errors)),
                  rmse_m=float(np.sqrt(np.mean(errors**2))), std_population_m=float(errors.std()),
                  max_error_m=float(errors.max()), min_error_m=float(errors.min()),
                  goal_motion_time_wall_s=float(sum(row['duration_s'] for row in rows)),
                  integration_duration_wall_s=data['duration_wall_s'])
    (DOCS/'report_metrics.json').write_text(json.dumps(result, ensure_ascii=False, indent=2)+'\n')
    return result


def pil_font(size=25, bold=False):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans'+('-Bold' if bold else '')+'.ttf', size)


def diagram(path, state=False):
    im = Image.new('RGB', (1400, 720 if not state else 640), '#f2f6fa')
    d = ImageDraw.Draw(im)
    def box(rect, title, lines, color='#e2edf6'):
        d.rounded_rectangle(rect, radius=18, fill=color, outline='#7c9ab4', width=3)
        x1, y1, x2, y2 = rect
        d.text((x1+18, y1+16), title, fill='#205b86', font=pil_font(24, True))
        for i, line in enumerate(lines): d.text((x1+18, y1+57+i*29), line, fill='#263c51', font=pil_font(19))
    def arrow(a, b, color='#6286a4'):
        d.line((*a, *b), fill=color, width=5)
        ang = math.atan2(b[1]-a[1], b[0]-a[0])
        d.polygon([b, (b[0]-18*math.cos(ang-.5), b[1]-18*math.sin(ang-.5)),
                   (b[0]-18*math.cos(ang+.5), b[1]-18*math.sin(ang+.5))], fill=color)
    if not state:
        d.text((35, 22), 'KIẾN TRÚC HỆ THỐNG BÀI 7', fill='#20374d', font=pil_font(30, True))
        box((30, 95, 320, 253), 'GIỌNG NÓI / TEXT', ['Micro → PCM 16 kHz', 'Vosk offline → văn bản', 'Nguồn + confidence'])
        box((380, 95, 700, 253), 'PHÂN TÍCH Ý ĐỊNH', ['Chuẩn hóa tiếng Việt', 'Khớp alias toàn tuyến', 'Ví dụ: A → B'])
        box((760, 95, 1110, 253), 'VOICE_NAVIGATOR', ['Kiểm tra readiness / goal', 'Action client tuần tự', 'Log, hủy, timeout'])
        arrow((320, 175), (380, 175)); arrow((700, 175), (760, 175))
        box((45, 367, 375, 552), 'BẢN ĐỒ NGỮ NGHĨA', ['map.yaml + map.pgm', 'Hạt giống → geodesic', 'regions.json + nhãn A/B/C', 'Mục tiêu known-free'])
        box((450, 367, 800, 552), 'LOCALIZATION', ['AMCL + LiDAR / odom', 'TF map → odom → base_link', 'Không điều khiển bằng', 'ground truth'])
        box((895, 367, 1365, 552), 'NAV2 + TURTLEBOT 4', ['NavigateToPose / planner / DWB', 'Costmap từ map + LiDAR', 'Robot và cảm biến mô phỏng', 'chạy trong Gazebo Fortress'])
        arrow((375, 410), (450, 410)); arrow((800, 455), (895, 455))
        arrow((935, 253), (1090, 367)); arrow((210, 367), (500, 253))
        d.text((40, 612), 'Dashboard: bản đồ có nhãn + TF pose + /plan + transcript + trạng thái', font=pil_font(25, True), fill='#205b86')
        d.text((40, 663), 'Dữ liệu thử nghiệm: log action, WAV tổng hợp, telemetry và ground truth chỉ đọc.', font=pil_font(20), fill='#526b80')
    else:
        d.text((35, 22), 'LUỒNG XỬ LÝ ĐIỀU HƯỚNG VÀ HỦY', fill='#20374d', font=pil_font(30, True))
        box((30, 103, 280, 238), 'IDLE / CHỜ', ['Câu mới → kiểm tra', 'Vùng / readiness'])
        box((370, 103, 655, 238), 'SENDING', ['send_goal_async()', 'Chờ accepted/rejected'])
        box((755, 103, 1060, 238), 'NAVIGATING', ['Feedback khoảng cách', 'Chờ kết quả action'])
        box((1110, 103, 1375, 238), 'KIỂM TRA ĐÍCH', ['status = 4', 'Sai số TF ≤ 0,4 m'])
        arrow((280, 168), (370, 168)); arrow((655, 168), (755, 168)); arrow((1060, 168), (1110, 168))
        box((60, 365, 380, 520), 'REJECTED / FAILED', ['Tên lạ, thiếu dữ liệu,', 'reject, abort hoặc lỗi', '→ không gửi chặng sau'], '#fae8e3')
        box((490, 365, 850, 520), 'CANCELING → CANCELED', ['Stop / pause / dữ liệu cũ', 'Hủy cả tuyến; xử lý handle', 'đến muộn sau yêu cầu hủy'], '#fff2d7')
        box((970, 365, 1365, 520), 'BETWEEN_GOALS', ['Còn chặng → SENDING', 'Hết chặng → SUCCEEDED', 'Không bỏ qua vùng nguồn'], '#e1f3e9')
        arrow((1240, 238), (1165, 365)); arrow((910, 238), (730, 365)); arrow((520, 238), (260, 365))
        d.text((50, 578), 'Đây là sơ đồ triển khai ứng dụng; hành vi tránh vật cản vẫn do Nav2 đảm nhiệm.', font=pil_font(21), fill='#526b80')
    im.save(path)


def make_figures(m):
    FIGURES.mkdir(parents=True, exist_ok=True)
    original = Image.open(ROOT/'maps/map.pgm').convert('RGB').resize((650, 650))
    segmented = Image.open(ROOT/'maps/segmented_map.png').convert('RGB').resize((650, 650))
    compare = Image.new('RGB', (1360, 725), 'white'); d = ImageDraw.Draw(compare)
    compare.paste(original, (10, 55)); compare.paste(segmented, (700, 55))
    d.text((20, 15), 'BẢN ĐỒ OCCUPANCY GỐC', font=pil_font(24, True), fill='#20374d')
    d.text((705, 15), 'PHÂN VÙNG CHỨC NĂNG A / B / C', font=pil_font(24, True), fill='#20374d')
    compare.save(FIGURES/'map_comparison.png')
    diagram(FIGURES/'architecture.png'); diagram(FIGURES/'navigation_states.png', True)
    plt.rcParams.update({'font.family': 'DejaVu Sans', 'font.size': 10})
    labels = ['A (lần 1)', 'B (đến lab)', 'A (tuyến A→B)', 'B (tuyến A→B)', 'C (hành lang)']
    fig, ax = plt.subplots(figsize=(9.4, 3.5))
    bars = ax.bar(labels, [row['error_m'] for row in m['goals']], color=['#64ade6','#a185d9','#64ade6','#a185d9','#65be9d'])
    ax.axhline(.25, color='#d1913f', linestyle='--', label='Tolerance vị trí Nav2: 0,25 m')
    ax.axhline(.4, color='#b9504b', linestyle=':', label='Hậu kiểm ứng dụng: 0,40 m')
    for bar in bars: ax.text(bar.get_x()+bar.get_width()/2, bar.get_height()+.007, f'{bar.get_height():.3f}', ha='center', fontsize=9)
    ax.set_ylim(0, .46); ax.set_ylabel('Sai số vị trí cuối (m)'); ax.grid(axis='y', alpha=.18); ax.legend(fontsize=8, loc='upper right')
    fig.tight_layout(); fig.savefig(FIGURES/'arrival_errors.png', dpi=180); plt.close(fig)
    fig, ax = plt.subplots(figsize=(9.4, 3.5))
    values = [row['duration_s'] for row in m['goals']]
    bars = ax.bar(labels, values, color='#4888b9')
    for bar, value in zip(bars, values): ax.text(bar.get_x()+bar.get_width()/2, value+1.2, f'{value:.2f}', ha='center', fontsize=9)
    ax.set_ylim(0, max(values)+16); ax.set_ylabel('Thời gian thực theo log action (s)'); ax.grid(axis='y', alpha=.18)
    fig.tight_layout(); fig.savefig(FIGURES/'goal_durations.png', dpi=180); plt.close(fig)
    data = read('artifacts/integration_results.json'); raw = read('maps/regions.json')
    fig, ax = plt.subplots(figsize=(7.5, 7.1))
    ax.imshow(Image.open(ROOT/'maps/segmented_map.png'), extent=[-10, 10.05, -10, 10.05], origin='upper')
    xy = np.array(data['ground_truth'])[:, 1:3]
    ax.plot(xy[:, 0], xy[:, 1], color='#d14d34', linewidth=1.8, label='Quỹ đạo ground truth lấy mẫu')
    ax.scatter(xy[0, 0], xy[0, 1], marker='o', color='#233b4f', s=45, label='Điểm bắt đầu lượt ghi')
    ax.scatter(xy[-1, 0], xy[-1, 1], marker='*', color='#233b4f', s=120, label='Điểm kết thúc')
    ax.set_xlabel('x trong frame map / world (m)'); ax.set_ylabel('y (m)'); ax.legend(loc='lower right', fontsize=8)
    ax.set_title('Quỹ đạo ghi trong Gazebo — 440 mẫu, chỉ đọc để đối chiếu', fontsize=11)
    fig.tight_layout(); fig.savefig(FIGURES/'recorded_trajectory.png', dpi=180); plt.close(fig)


class Report:
    def __init__(self):
        self.doc = Document()
        section = self.doc.sections[0]
        section.page_width, section.page_height = Cm(21), Cm(29.7)
        section.top_margin, section.bottom_margin = Cm(1.9), Cm(1.8)
        section.left_margin, section.right_margin = Cm(2.2), Cm(1.8)
        section.header_distance, section.footer_distance = Cm(.8), Cm(.8)
        styles = self.doc.styles
        for name in ['Normal','Body Text','Heading 1','Heading 2','Heading 3','Caption']:
            styles[name].font.name = 'Times New Roman'
            styles[name]._element.rPr.rFonts.set(qn('w:eastAsia'), 'Times New Roman')
        normal = styles['Normal']; normal.font.size = Pt(11.5)
        normal.paragraph_format.space_after = Pt(5)
        normal.paragraph_format.line_spacing = 1.15
        normal.paragraph_format.widow_control = True
        for name, size in [('Heading 1',15),('Heading 2',12.5),('Heading 3',11.5)]:
            styles[name].font.size = Pt(size); styles[name].font.bold = True
            styles[name].font.color.rgb = RGBColor.from_string(BLUE)
            styles[name].paragraph_format.space_before = Pt(8)
            styles[name].paragraph_format.space_after = Pt(6)
        styles['Caption'].font.size = Pt(10)
        styles['Caption'].font.italic = True
        code = styles.add_style('Code Block', 1)
        code.font.name = 'DejaVu Sans Mono'; code.font.size = Pt(8.2)
        code.paragraph_format.line_spacing = 1.0
        code.paragraph_format.space_before = Pt(3); code.paragraph_format.space_after = Pt(5)
        header = section.header.paragraphs[0]
        header.alignment = WD_ALIGN_PARAGRAPH.RIGHT
        run = header.add_run('BÀI 7  |  SEMANTIC MAPPING & VOICE NAVIGATION')
        run.font.name = 'Arial'; run.font.size = Pt(8); run.font.color.rgb = RGBColor.from_string('6D7F91')
        footer = section.footer.paragraphs[0]
        footer.alignment = WD_ALIGN_PARAGRAPH.CENTER
        footer.add_run('Báo cáo chi tiết • TurtleBot 4 / ROS 2 Humble   |   Trang ')
        self.field(footer, 'PAGE'); footer.add_run(' / '); self.field(footer, 'NUMPAGES')
        for run in footer.runs: run.font.size = Pt(9)
        self.contents = []
        self.section_number = 0
        self.fig_number = self.table_number = 0
        self.doc.core_properties.title = 'Bài 7 — Phân vùng bản đồ và điều hướng robot bằng giọng nói'
        self.doc.core_properties.subject = 'Báo cáo chi tiết triển khai và kiểm thử TurtleBot 4 / Nav2'
        self.doc.core_properties.author = 'Sinh viên thực hiện'
        self.doc.core_properties.created = datetime.now(timezone.utc)
        self.doc.core_properties.modified = datetime.now(timezone.utc)
        self.doc.core_properties.keywords = 'ROS 2 Humble, TurtleBot 4, Nav2, Vosk, semantic mapping'
        update = OxmlElement('w:updateFields'); update.set(qn('w:val'),'true')
        self.doc.settings.element.append(update)

    @staticmethod
    def field(paragraph, code):
        run = paragraph.add_run(); field = OxmlElement('w:fldSimple'); field.set(qn('w:instr'), code)
        inner = OxmlElement('w:r'); text = OxmlElement('w:t')
        reference = re.search(r'PAGEREF chapter_(\d+)', code)
        text.text = str(int(reference.group(1))+1) if reference else '25' if code == 'NUMPAGES' else '1'
        inner.append(text); field.append(inner)
        run._r.addnext(field)

    def p(self, text, bold=False, style=None):
        paragraph = self.doc.add_paragraph(style=style)
        if not style: paragraph.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        run = paragraph.add_run(str(text)); run.bold = bold
        return paragraph

    def paragraphs(self, text):
        for block in text.strip().split('\n\n'):
            self.p(' '.join(block.split()))

    def heading(self, text, level=2):
        return self.doc.add_heading(text, level)

    def page(self, title):
        self.doc.add_page_break()
        self.section_number += 1
        heading = self.doc.add_heading(title, 1)
        bookmark = f'chapter_{self.section_number}'
        start = OxmlElement('w:bookmarkStart'); start.set(qn('w:id'),str(self.section_number)); start.set(qn('w:name'),bookmark)
        end = OxmlElement('w:bookmarkEnd'); end.set(qn('w:id'),str(self.section_number))
        heading._p.insert(0, start); heading._p.append(end)
        self.contents.append((title, bookmark))

    def bullet(self, text):
        return self.p(text, style='List Bullet')

    def code(self, text):
        p = self.p(text.strip(), style='Code Block')
        shade = OxmlElement('w:shd'); shade.set(qn('w:fill'),'F0F3F7'); p._p.get_or_add_pPr().append(shade)
        return p

    def table(self, headers, rows, widths=None, caption=None, size=10):
        if caption:
            self.table_number += 1
            self.p(f'Bảng {self.table_number}. {caption}', style='Caption')
        table = self.doc.add_table(rows=1, cols=len(headers))
        table.style = 'Table Grid'
        for cell, value in zip(table.rows[0].cells, headers):
            cell.text = str(value)
            shade=OxmlElement('w:shd');shade.set(qn('w:fill'),'E4EDF5');cell._tc.get_or_add_tcPr().append(shade)
        repeat=OxmlElement('w:tblHeader');table.rows[0]._tr.get_or_add_trPr().append(repeat)
        for values in rows:
            for cell, value in zip(table.add_row().cells, values): cell.text = str(value)
        for row_i, row in enumerate(table.rows):
            cant=OxmlElement('w:cantSplit');row._tr.get_or_add_trPr().append(cant)
            for cell_i, cell in enumerate(row.cells):
                if widths: cell.width = Cm(widths[cell_i])
                for p in cell.paragraphs:
                    p.paragraph_format.space_after = Pt(3)
                    p.paragraph_format.line_spacing = 1.04
                    for run in p.runs:
                        run.font.name='Times New Roman';run.font.size=Pt(size);run.bold=row_i == 0
        self.doc.add_paragraph().paragraph_format.space_after = Pt(1)
        return table

    def figure(self, path, caption, width=16.5):
        paragraph = self.doc.add_paragraph(); paragraph.alignment=WD_ALIGN_PARAGRAPH.CENTER
        paragraph.add_run().add_picture(str(path), width=Cm(width))
        paragraph.paragraph_format.keep_with_next = True
        self.fig_number += 1
        p=self.p(f'Hình {self.fig_number}. {caption}',style='Caption');p.alignment=WD_ALIGN_PARAGRAPH.CENTER

    def cover(self):
        self.doc.add_paragraph('BÁO CÁO THỰC HÀNH',style='Title').alignment=WD_ALIGN_PARAGRAPH.CENTER
        p=self.doc.add_paragraph('HỌC PHẦN TƯƠNG TÁC NGƯỜI – ROBOT')
        p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        p.paragraph_format.space_after=Pt(42)
        p=self.doc.add_paragraph('BÀI THỰC HÀNH 7')
        p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        p.runs[0].bold=True;p.runs[0].font.size=Pt(23);p.runs[0].font.color.rgb=RGBColor.from_string(BLUE)
        p=self.doc.add_paragraph('PHÂN VÙNG BẢN ĐỒ VÀ\nĐIỀU HƯỚNG ROBOT BẰNG GIỌNG NÓI')
        p.alignment=WD_ALIGN_PARAGRAPH.CENTER
        p.runs[0].bold=True;p.runs[0].font.size=Pt(20)
        p.paragraph_format.space_after=Pt(16)
        p=self.doc.add_paragraph('Ubuntu 22.04 • ROS 2 Humble • TurtleBot 4 Simulation\nNav2 • Semantic Mapping • Vosk tiếng Việt')
        p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.runs[0].font.size=Pt(12)
        self.doc.add_paragraph()
        self.figure(ROOT/'maps/segmented_map.png','Ba vùng chức năng A, B và C trên bản đồ mê cung.',width=9)
        for value in ['Sinh viên thực hiện: .....................................................................',
                      'Mã số sinh viên: ...........................................................................',
                      'Lớp / Nhóm: ................................................................................',
                      'Giảng viên hướng dẫn: ................................................................']:
            p=self.doc.add_paragraph(value);p.paragraph_format.space_after=Pt(6)
        p=self.doc.add_paragraph('Ngày lập báo cáo: 07/11/2026\nBản báo cáo chi tiết – bổ sung cho bản PDF tóm tắt 2 trang')
        p.alignment=WD_ALIGN_PARAGRAPH.CENTER;p.runs[0].font.size=Pt(10)


def build_report():
    DOCS.mkdir(exist_ok=True)
    m = metrics(); make_figures(m)
    validation = read('artifacts/validation.json')
    integration = read('artifacts/integration_results.json')
    regions = read('maps/regions.json')
    asr = read('artifacts/asr_google/asr_results.json')
    runtime_asr = read('artifacts/live_decoder_validation.json')
    r = Report(); r.cover()

    r.page('TÓM TẮT BÁO CÁO VÀ PHẠM VI KẾT QUẢ')
    r.paragraphs('''Bài thực hành xây dựng một hệ thống điều hướng có lớp ngữ nghĩa cho robot TurtleBot 4 trong môi trường mô phỏng. Thay vì chỉ định trực tiếp một cặp tọa độ trên RViz, người dùng có thể nói tên khu vực hoặc một chuỗi khu vực cần đi qua. Hệ thống phải chuyển giọng nói thành văn bản, hiểu đúng thứ tự tuyến, xác định các đích hợp lệ trên bản đồ và giao việc di chuyển cho Nav2.

Giải pháp gồm ba phần chính: phân vùng bản đồ Occupancy Grid theo hạt giống chức năng, nhận dạng và phân tích câu tiếng Việt, và một ROS 2 node quản lý action NavigateToPose tuần tự. Giao diện hiển thị bản đồ có nhãn, câu ASR đang xử lý, tuyến đã hiểu, vị trí TF của robot, đường kế hoạch và trạng thái thực thi. Các quyết định được ghi log để đối chiếu sau thử nghiệm.

Kết quả thực nghiệm được chia thành các tầng bằng chứng. Kiểm thử logic và action server giả xác nhận các quy tắc chương trình. Bộ WAV tiếng Việt tổng hợp kiểm tra phần âm thanh – ASR – parser. Thử nghiệm tích hợp sử dụng kết quả giải mã thực để điều hướng robot trong Gazebo với Nav2 thật. Không xem âm thanh tổng hợp là bản ghi giọng nói của sinh viên và không dùng hoạt cảnh giả để thay chuyển động robot.''')
    r.table(['Chỉ tiêu','Kết quả kiểm chứng'],[
        ['Số khu vực có nhãn','3: A – Phòng học; B – Phòng thí nghiệm; C – Hành lang'],
        ['Kiểm thử tự động','19: 10 core + 3 decoder/UTF-8 + 6 luồng action giả'],
        ['Điều hướng trong Gazebo','4 tuyến hợp lệ / 5 goal Nav2 thành công'],
        ['Khu vực không tồn tại','D được nhận dạng là “đê”, parser từ chối, không gửi goal'],
        ['Sai số vị trí lớn nhất',f"{m['max_error_m']:.3f} m; trung bình {m['mean_error_m']:.3f} m"],
        ['Dữ liệu ground truth','440 mẫu chỉ đọc để đối chiếu; không dùng làm bộ điều khiển'],
        ['Video demo','264,2 giây; hình Nav2/Gazebo thật; âm thanh đầu vào tổng hợp'],
        ['GitHub public','Chưa xác nhận push public; source đã có repository local']
    ],caption='Tóm tắt các kết quả và trạng thái nộp bài.')
    r.paragraphs('''Các tên phòng trong báo cáo là nhãn chức năng do người dùng gán trên world maze, không phải kết quả nhận diện kiến trúc phòng từ ảnh. Bản phân vùng hiện tại là bán tự động: con người định nghĩa hạt giống và tên, thuật toán tự lan nhãn trên vùng free. Những giới hạn này được giữ nhất quán trong mô tả, bảng kết quả và kết luận.''')

    r.page('MỤC LỤC VÀ QUY ƯỚC ĐỌC BÁO CÁO')
    toc_anchor=r.doc.add_paragraph('Mục lục dưới đây có số trang tham chiếu; có thể cập nhật trường trong Word bằng Ctrl+A → F9.')
    toc_paragraphs=[]
    # Create entries now; their bookmarks are filled after all chapters exist.
    for _ in range(22): toc_paragraphs.append(r.doc.add_paragraph())
    r.heading('Quy ước và thuật ngữ')
    r.table(['Thuật ngữ','Ý nghĩa sử dụng trong báo cáo'],[
        ['Occupancy Grid','Lưới ô mô tả vùng đã biết trống, vật cản và vùng chưa biết.'],
        ['Semantic region','Vùng hình học gắn ID/tên, alias và một goal điều hướng.'],
        ['ASR / STT','Chuyển tín hiệu tiếng nói thành văn bản.'],
        ['Goal / route','Goal là một đích; route là chuỗi ID khu vực có thứ tự.'],
        ['Clearance','Khoảng cách từ tâm ô/robot đến phần biên được kiểm tra.'],
        ['Ground truth','Vị trí mô phỏng dùng chỉ đọc cho initial pose/đối chiếu theo phạm vi nêu rõ.'],
        ['Mock / synthetic','Server giả phục vụ test / âm thanh được tổng hợp, không phải giọng người thật.']
    ],size=10)

    r.page('1. MỤC TIÊU, YÊU CẦU VÀ TIÊU CHÍ NGHIỆM THU')
    r.heading('1.1. Bài toán cần giải quyết')
    r.paragraphs('''Trong ứng dụng robot phục vụ ở trường học hoặc phòng thí nghiệm, người vận hành thường nhớ tên khu vực hơn là tọa độ x, y. Một giao diện chỉ có nút Nav2 Goal vẫn đòi hỏi người dùng hiểu bản đồ và trực tiếp chọn vị trí. Bài thực hành bổ sung lớp ngữ nghĩa để liên kết ngôn ngữ tự nhiên với các đích được khảo sát sẵn.

Đầu vào là bản đồ 2D đã tạo từ trước và một câu nói tiếng Việt. Đầu ra không chỉ là ID vùng được nhắc đến mà còn là một trình tự NavigateToPose có kiểm tra điều kiện. Khi câu nói yêu cầu “từ A đến B”, vùng nguồn A là một điểm phải đi qua; vị trí hiện tại khác A không được làm chương trình tự bỏ A và chạy thẳng đến B.''')
    r.table(['Yêu cầu','Cách đáp ứng','Bằng chứng'],[
        ['Tối thiểu 3 vùng','Geodesic Voronoi với 3 hạt giống A/B/C','Ảnh segmented_map.png; lưới nhãn; regions.json'],
        ['Đích hợp lệ','Known-free, đúng vùng, clearance ≥0,32 m','Kiểm thử map; metadata từng goal'],
        ['Tối thiểu 3 câu lệnh','Alias tên phòng/ID; hỗ trợ nguồn–đích','Test parser; WAV → ASR; log tích hợp'],
        ['Di chuyển và tránh vật cản','Nav2 + LiDAR + AMCL trên TurtleBot 4','Action status; TF cuối; telemetry Gazebo'],
        ['Xử lý khu vực lạ','Từ chối toàn tuyến trước send_goal','Ca D/đê; test vùng Z trong tuyến'],
        ['Source, video, báo cáo','Repository local, ZIP, MP4, PDF và Word','GitHub public còn chờ kết nối']
    ],caption='Đối chiếu yêu cầu đề bài với thiết kế và bằng chứng.')
    r.heading('1.2. Tiêu chí đánh giá được chọn')
    r.paragraphs('''Một tuyến hợp lệ chỉ được coi là hoàn thành khi mọi goal xuất hiện đúng thứ tự, đều có status=4 và thỏa kiểm tra sai số vị trí sau action. Ca vùng lạ được coi là xử lý đúng nếu có thông báo từ chối và không xuất hiện GOAL_SENT. Bộ kiểm thử còn theo dõi các sự kiện hazard từ driver để phát hiện lỗi trong lượt chạy.

Thời gian thực hiện một tuần là thời hạn của đề bài, không được dùng để suy ra rằng đã đo liên tục một tuần. Các con số trong báo cáo là dữ liệu từ lượt kiểm thử ngày 07/11/2026 được lưu trong artifacts. Những mở rộng chưa triển khai được trình bày riêng, không tính như tiêu chí đã đạt.''')

    r.page('2. MÔI TRƯỜNG, CÔNG NGHỆ VÀ CẤU TRÚC SOURCE')
    r.paragraphs('''Hệ thống triển khai trên Ubuntu 22.04 với ROS 2 Humble và TurtleBot 4 Lite trong Ignition Gazebo Fortress. Nav2 thực hiện lập kế hoạch và điều khiển; AMCL ước lượng pose trên bản đồ tĩnh. Python được dùng cho xử lý bản đồ, nhận dạng lời nói, giao diện và action client. Venv có system-site-packages để dùng các binding rclpy của bản cài ROS apt.''')
    r.table(['Thành phần','Công nghệ / cấu hình','Vai trò'],[
        ['Robot mô phỏng','TurtleBot 4 Lite + Create 3','Chuyển động, odometry, dock, hazard và LiDAR'],
        ['Điều hướng','Nav2; NavFn planner; DWB controller','Tạo đường và vận tốc tránh vật cản'],
        ['Định vị','AMCL; chuỗi TF map/odom/base_link','Pose trong frame map'],
        ['Bản đồ','PGM 401×401; 0,05 m/ô','Occupancy Grid gốc cho maze'],
        ['Xử lý ảnh','OpenCV + NumPy + Pillow','Mask free, distance transform, nhãn và ảnh minh họa'],
        ['Giọng nói','arecord; Vosk 0.3.45; small-vn-0.4','Thu PCM và nhận dạng tiếng Việt offline'],
        ['Giao diện','Tkinter + Pillow','Bản đồ semantic, transcript, trạng thái và video'],
        ['Kiểm chứng','unittest; mock action; log JSON/JSONL','Tách test logic và thử nghiệm simulator']
    ],caption='Các thành phần phần mềm chính.')
    r.heading('2.1. Hai package ROS được sử dụng')
    r.code('''src/
  turtlebot4_slam_nav/    # launch world, AMCL, Nav2, config, bản đồ
  turtlebot4_voice_nav/
    turtlebot4_voice_nav/ # segmentation, commands, navigator, speech, dashboard
    maps/                # map gốc + lưới nhãn + regions.json + ảnh phân vùng
    config/              # hạt giống và các nhãn chức năng
    test/                # kiểm thử logic, action và decoder
    tools/               # chuẩn bị sim, kiểm chứng, tạo demo/báo cáo
    artifacts/           # log, WAV, video, thống kê
    docs/                # PDF tóm tắt và Word chi tiết''')
    r.paragraphs('''Package turtlebot4_slam_nav là phần hỗ trợ được dùng lại từ bài trước, cung cấp launcher và cấu hình mô phỏng. Chức năng mới của Bài 7 nằm trong turtlebot4_voice_nav. Khi đóng gói cần giữ cả hai package; chỉ chép node nhận giọng nói mà bỏ launcher/map/config sẽ không tạo được một workspace có thể tái hiện.

Repository nộp không chứa venv, weights ASR, build/install/log hoặc dữ liệu tài khoản. Model được tải qua công cụ riêng và lưu ở cache người dùng. Kiểm tra build trên workspace tách biệt được dùng để giảm nguy cơ vô tình phụ thuộc các package ngoài bộ nộp.''')

    r.page('3. KIẾN TRÚC TỔNG THỂ VÀ LUỒNG DỮ LIỆU')
    r.figure(FIGURES/'architecture.png','Các lớp xử lý và liên kết tới Nav2/Gazebo.',16.7)
    r.heading('3.1. Phân tách xử lý offline và online')
    r.paragraphs('''Ở bước offline, chương trình đọc map.yaml, map.pgm và cấu hình hạt giống; tạo region_labels.npy, ảnh tô màu và regions.json. Đây là dữ liệu có thể xem xét trước khi robot chạy. Các tọa độ đích được kiểm tra ngay trong bước tạo dữ liệu và kiểm tra lại lúc node điều hướng khởi động.

Ở bước online, microphone hoặc ô nhập văn bản tạo một thông điệp lệnh. Parser biến thông điệp thành một Command chứa kind, route và reason. Node điều hướng kiểm tra tên vùng, mức tin cậy nếu nguồn là microphone, trạng thái robot và readiness của Nav2. Chỉ khi các kiểm tra đạt, action client mới gửi goal đầu tiên.

Trong lúc robot đi, feedback cập nhật khoảng cách còn lại; chuỗi TF cung cấp vị trí trong bản đồ; /plan cung cấp đường kế hoạch cho giao diện. Khi action trả kết quả, ứng dụng hậu kiểm vị trí trước khi tăng chỉ số chặng. Các sự kiện có ý nghĩa được ghi JSONL với thời gian thực và thời gian mô phỏng.''')
    r.heading('3.2. Tại sao tách dashboard khỏi bộ điều hướng?')
    r.paragraphs('''Dashboard là công cụ nhập lệnh và quan sát. Nó không tự tính quỹ đạo để vẽ robot chạy thay cho simulator. Tách giao diện và node action cho phép kiểm thử parser/action không cần màn hình, đồng thời hỗ trợ gửi câu lệnh từ công cụ ROS khác. Nếu dashboard không nhận heartbeat, người dùng thấy trạng thái mất kết nối thay vì một hoạt cảnh tiếp tục chạy.

Giọng nói và lệnh TEXT được ghi khác nguồn. Âm thanh tổng hợp dùng trong kiểm thử cũng có nhãn SYNTHETIC_AUDIO riêng. Việc phân biệt nguồn giúp đánh giá đúng phạm vi bằng chứng: một nút câu mẫu hoạt động không chứng minh microphone đã nhận đúng câu của người nói.''')

    r.page('4. BẢN ĐỒ OCCUPANCY GRID VÀ BIẾN ĐỔI TỌA ĐỘ')
    r.heading('4.1. Ý nghĩa dữ liệu bản đồ')
    r.paragraphs('''Ảnh PGM lưu mức xám của từng ô, trong khi file YAML lưu độ phân giải, origin, chế độ và hai ngưỡng diễn giải occupancy. Ảnh là ma trận hàng–cột với gốc ở góc trên trái; frame map của ROS dùng đơn vị mét và hướng trục riêng. Vì vậy vị trí nhìn thấy trên ảnh không thể đưa trực tiếp vào PoseStamped.

Với negate=0, occupancy p=1−I/255, trong đó I là giá trị xám. Ô được xem là free nếu p<free_thresh và occupied nếu p>occupied_thresh; khoảng giữa là unknown. Chương trình giữ unknown ngoài vùng có thể gán đích, kể cả khi nó không phải một pixel đen của tường.''')
    r.code('''image: map.pgm
mode: trinary
resolution: 0.05
origin: [-10, -10, 0]
negate: 0
occupied_thresh: 0.65
free_thresh: 0.196''')
    r.heading('4.2. Công thức từ tâm pixel sang tọa độ map')
    r.code('''x_local = (column + 0.5) × resolution
y_local = (height - row - 0.5) × resolution
x_map = origin_x + cos(yaw)×x_local - sin(yaw)×y_local
y_map = origin_y + sin(yaw)×x_local + cos(yaw)×y_local''')
    r.paragraphs('''Hệ số 0,5 chọn tâm ô thay vì góc ô. Thành phần height−row−0,5 đảo chiều hàng ảnh để phù hợp trục y. Khi origin yaw khác 0, bỏ bước quay sẽ gây sai số tăng theo khoảng cách tới gốc. Phép nghịch đảo đưa điểm map về hệ local, chia resolution và floor để tìm ô chứa điểm.

Trên bản đồ 401×401 ô, vùng ảnh có kích thước 20,05×20,05 m. Goal A ở (−2,−3) thuộc pixel (160,260), goal B thuộc (240,260), goal C thuộc (160,120). Tọa độ goal lưu trong JSON là tọa độ được khảo sát; tâm ô chứa A là (−1,975; −2,975), nên không nên nhầm “goal nằm trong ô” với “goal chính xác bằng tâm ô”.''')
    r.table(['Kiểm tra tọa độ','Mục đích'],[
        ['Round-trip pixel → world → pixel','Trả về đúng ô, kể cả origin có góc quay.'],
        ['Điểm ngoài ảnh / NaN','Không được xem là goal hợp lệ.'],
        ['Điểm trên occupied/unknown','Bị loại trước khi gửi Nav2.'],
        ['Ảnh map và metadata semantic','Đối chiếu SHA-256 để tránh dùng nhầm ảnh bản đồ.']
    ],caption='Những kiểm tra giúp tránh sai hệ tọa độ.')

    r.page('5. PHƯƠNG PHÁP PHÂN VÙNG BÁN TỰ ĐỘNG')
    r.heading('5.1. Lựa chọn phương pháp geodesic Voronoi')
    r.paragraphs('''Mê cung có nhiều lối nối và vùng trống liên thông. Chỉ dùng connected components trên free mask có thể cho một vùng rất lớn thay vì các khu chức năng. Mặt khác, mục tiêu của bài cho phép bắt đầu từ vùng được vẽ/định nghĩa thủ công. Do đó giải pháp chọn hạt giống chức năng và dùng khoảng cách đường đi để chia các ô còn lại.

Mỗi hạt giống có ID và tên. Thuật toán lan đồng thời từ tất cả hạt giống trên lưới free với lân cận bốn hướng. Ô nhận nhãn của hạt giống tới nó bằng số bước ít nhất. Khoảng cách này chịu ảnh hưởng cấu trúc lối đi: hai điểm gần nhau theo đường thẳng nhưng cách bởi tường có thể thuộc các nhánh khác nhau.

Triển khai dùng priority queue lưu (distance, label, row, column). Ban đầu nhãn seed bằng chỉ số vùng, distance=0; các ô khác có distance vô cùng và label=0. Khi lấy một ô ra, thuật toán xét bốn ô kề còn trong ảnh và thuộc free mask, cập nhật nếu có đường ngắn hơn. Chỉ cập nhật khi distance mới nhỏ hơn giúp kết quả ổn định với thứ tự xử lý đã xác định.''')
    r.code('''for each semantic seed i:
    check seed is known-free and has sufficient clearance
    label[seed_i] = i; distance[seed_i] = 0
    push seed_i into priority queue
while queue is not empty:
    pop cell with smallest distance
    for neighbor in four-connected known-free cells:
        if distance[current] + 1 < distance[neighbor]:
            update distance and copy semantic label
            push neighbor
keep all unknown, occupied, disconnected cells unlabelled''')
    r.heading('5.2. Tính chất, chi phí và giới hạn')
    r.paragraphs('''Với V ô được thăm và tối đa bốn cạnh mỗi ô, bản triển khai priority queue có chi phí xấp xỉ O(V log V) và bộ nhớ O(V). Vì trọng số các cạnh đều bằng một, có thể thay bằng multi-source BFS để đạt O(V+E); đó là hướng tối ưu hóa, chưa phải cách đang chạy trong source hiện tại.

Phân vùng này không chứng minh vùng A là một phòng học về mặt kiến trúc hay chức năng thực tế. Tên vùng được gán bởi người dùng; thuật toán chỉ chia miền hình học có thể đi. Nếu thay bản đồ hoặc thay seed, phải tạo lại metadata, kiểm tra đích và xem lại ranh giới. Thành phần free không nối bất kỳ seed nào vẫn có label=0; kết quả hiện tại có 187 ô free chưa gán, tương đương 0,4675 m².''')

    r.page('6. GẮN NHÃN, DỮ LIỆU VÙNG VÀ ĐÍCH HỢP LỆ')
    r.figure(FIGURES/'map_comparison.png','Bản đồ gốc và bản đồ phân vùng, giữ nguyên tường/unknown.',16.7)
    r.table(['ID / Tên','Goal (x, y, yaw)','Ô (c,r)','Diện tích','Clearance'],[
        [f"{x['id']} – {x['name']}",f"({x['goal']['x']:.1f}; {x['goal']['y']:.1f}; {x['goal']['yaw']:.3f})",
         f"({x['goal_pixel'][0]},{x['goal_pixel'][1]})",f"{x['area_m2']:.4f} m²",f"{x['clearance_m']:.3f} m"] for x in regions['regions']
    ],caption='Các vùng và goal đã lưu trong regions.json.',size=9)
    r.paragraphs('''Diện tích vùng là số ô mang nhãn nhân resolution². Với resolution 0,05 m, mỗi ô tương ứng 0,0025 m². Tổng diện tích ba vùng khoảng 220,2775 m²; con số này chỉ là diện tích free được gán nhãn trên bản đồ hiện có, không phải diện tích kiến trúc chính xác của từng phòng.

Khoảng trống được tính bằng distance transform trên free mask có padding mép ảnh. Tường, unknown và ô ngoài ảnh đều không được coi là free. Hạt giống và goal cần clearance tối thiểu 0,32 m. Chương trình còn kiểm tra goal nằm đúng label của vùng, nhằm tránh trường hợp tên vùng được gắn với một điểm ở nhánh khác.''')
    r.heading('6.1. Các trường quan trọng trong metadata')
    r.code('''{
  "id": "B", "name": "Phòng thí nghiệm",
  "aliases": ["khu vực b", "khu vực bê", "phòng thí nghiệm"],
  "goal": {"x": 2.0, "y": -3.0, "yaw": 0.0},
  "goal_pixel": [240, 260], "clearance_m": 0.95,
  "area_m2": 73.2625,
  "polygons": ["các đỉnh biên vùng trong frame map"]
}''')
    r.paragraphs('''Đoạn JSON trên rút gọn phần polygons để dễ đọc; tọa độ biên đầy đủ nằm trong file thực tế. Ảnh bản đồ có mã băm SHA-256 trong metadata. Node từ chối khởi động nếu ảnh không khớp mã băm, tránh sử dụng điểm đích đã kiểm tra trên một ảnh khác.''')

    r.page('7. THU ÂM VÀ NHẬN DẠNG GIỌNG NÓI TIẾNG VIỆT')
    r.heading('7.1. Luồng xử lý âm thanh')
    r.paragraphs('''Microphone được đọc bằng arecord qua thiết bị ALSA mặc định. Định dạng PCM là mono, 16 kHz, signed int16. Worker đọc từng block 4.000 byte, tương ứng 2.000 mẫu hay 0,125 giây âm thanh. Luồng thu/chạy ASR tách khỏi vòng cập nhật Tkinter nên giao diện không phải chờ từng lần giải mã mới vẽ được bản đồ.

Vosk small-vn-0.4 xử lý âm thanh offline. Các mẫu câu trong grammar hướng bộ giải mã về miền lệnh điều hướng, nhưng grammar vẫn giữ [unk] và một số tên vùng ngoài danh sách để có thể từ chối. Việc thu âm hằng ngày không gọi Google TTS; Google TTS chỉ tạo các câu mẫu thử nghiệm được cache trước đó.

Kết quả tạm dùng để hiển thị người dùng đang nói gì. Lệnh di chuyển chỉ được gửi từ kết quả cuối câu; nếu gửi ngay từ một partial “đi đến A”, người nói có thể chưa nói xong “rồi đến B”. Các câu Stop/Hủy là trường hợp riêng có thể xử lý sớm. Cửa sổ âm thanh tối đa 8 giây giúp tránh chờ vô hạn khi tiếng nền làm Vosk không tìm được điểm hết câu.''')
    r.table(['Thông số','Giá trị / cách dùng'],[
        ['Tần số mẫu / kênh / mẫu','16.000 Hz / 1 / int16'],
        ['Kích thước block','4.000 byte, xấp xỉ 125 ms'],
        ['Model','vosk-model-small-vn-0.4, lưu cache người dùng'],
        ['Ngưỡng lệnh microphone','Confidence ≥0,65; hủy không bị xử lý như lệnh di chuyển'],
        ['Kết quả tạm','Hiển thị transcript, chưa gửi tuyến điều hướng'],
        ['Kết thúc đoạn','Endpoint ASR hoặc chốt cửa sổ 8 giây'],
        ['Dữ liệu người dùng','Không tự lưu bản thu mic thành file; có log transcript theo thao tác']
    ],caption='Cấu hình nhận dạng và ý nghĩa vận hành.')
    r.heading('7.2. Confidence và chất lượng tín hiệu')
    r.paragraphs('''Confidence được lấy từ các từ nhận dạng, không phải giá trị do giao diện tự gán. Một câu có confidence cao vẫn có thể sai tên khu vực; ví dụ trong quá trình phát triển đã có hiện tượng tên vùng ngoài danh sách bị ép về âm gần giống của vùng hợp lệ. Vì vậy threshold chỉ là một lớp kiểm tra, không thể thay thế kiểm tra ngữ nghĩa hoặc đánh giá trên giọng người thật.

Nếu thanh mức âm gần tối đa liên tục, cần kiểm tra gain/boost của micro thay vì tiếp tục tăng độ nhạy. Mẫu bị clipping làm mất thông tin âm học và có thể khiến ASR giữ partial hoặc nhận sai. Bài 7 giữ cấu hình mức thu đã được điều chỉnh từ bài trước; người dùng nên thử lại trong môi trường yên tĩnh trước khi quay demo.''')

    r.page('8. CHUẨN HÓA VĂN BẢN, ALIAS VÀ TUYẾN NHIỀU ĐÍCH')
    r.heading('8.1. Từ transcript tới Command')
    r.paragraphs('''Parser chuyển văn bản sang chữ thường, xử lý chữ đ, bỏ dấu kết hợp Unicode và chuẩn hóa khoảng trắng. Các alias được chuẩn hóa bằng cùng một hàm để so khớp không phụ thuộc hoa/thường hay dấu. Đối tượng Command mang kind, route có thứ tự và reason phục vụ phản hồi.

Danh mục alias hỗ trợ “khu vực A”, “phòng A”, “phòng học”, cách đọc B là “bê” và C là “xê”. Alias là dữ liệu ánh xạ tên sang ID; nếu cùng một alias chuẩn hóa trỏ đến hai vùng khác nhau, chương trình báo lỗi thay vì chọn ngẫu nhiên. Trong bản hiện tại, parser ưu tiên sự rõ ràng hơn là đoán bằng fuzzy matching.''')
    r.table(['Câu đầu vào','Kết quả phân tích','Ý nghĩa'],[
        ['Đi đến khu vực A.','NAVIGATE → [A]','Một đích có ID.'],
        ['Đi đến phòng thí nghiệm.','NAVIGATE → [B]','Tên semantic được ánh xạ sang ID.'],
        ['Di chuyển từ A đến B.','NAVIGATE → [A,B]','Không bỏ chặng nguồn A.'],
        ['Đi từ phòng A qua hành lang C rồi đến phòng B.','NAVIGATE → [A,C,B]','Tuyến mở rộng nhiều điểm.'],
        ['Đi từ A qua Z rồi đến B.','UNKNOWN_REGION → []','Từ chối toàn tuyến.'],
        ['Không đi đến A.','INVALID → []','Không biến câu phủ định thành lệnh đi.'],
        ['Dừng lại.','CANCEL','Hủy goal đang chạy và phần còn lại.']
    ],caption='Một số mẫu phân tích và cách xử lý.',size=10)
    r.heading('8.2. Quy tắc không bỏ qua thông tin không hiểu')
    r.paragraphs('''Sau động từ điều hướng, parser tách tuyến theo các liên từ như từ/đến/qua/rồi đến. Mỗi đoạn phải khớp toàn bộ một alias. “Phòng học ngoài sân” không được cắt còn “phòng học” để tiếp tục chạy; tương tự, một vùng Z ở giữa tuyến không bị bỏ qua chỉ vì A và B ở hai đầu vẫn hợp lệ.

Chuỗi [unk] được giữ trong transcript để parser từ chối. Nếu xóa nhãn này, một câu vốn thiếu từ có thể trở thành lệnh tưởng như đúng. Số chặng tối đa là tám; hai ID trùng nhau liên tiếp được gộp, nhưng thứ tự các vùng khác nhau được giữ. Chương trình chưa hỗ trợ hiểu tất cả cấu trúc tiếng Việt tự do, đại từ mơ hồ hoặc đối thoại hỏi lại nhiều lượt; các trường hợp ngoài grammar cần nói lại bằng câu mẫu.''')

    r.page('9. ĐIỀU HƯỚNG BẰNG NAV2 VÀ QUẢN LÝ ACTION')
    r.figure(FIGURES/'navigation_states.png','Luồng action và các nhánh hủy/lỗi của node voice_navigator.',16.7)
    r.heading('9.1. Tạo NavigateToPose goal')
    r.paragraphs('''Sau khi route được kiểm tra, node lấy x, y, yaw của vùng đầu trong regions.json. PoseStamped có frame_id=map, timestamp theo ROS clock và quaternion từ yaw. Với chuyển động phẳng: qz=sin(yaw/2), qw=cos(yaw/2); qx=qy=0. Không đưa pixel hoặc tọa độ world tùy ý vào action đang mong frame map.

send_goal_async cho phép chờ server nhận goal mà không khóa vòng xử lý. Goal handle được dùng để theo dõi kết quả và gửi cancel. Chương trình phân biệt giai đoạn SENDING với NAVIGATING vì người dùng có thể yêu cầu hủy trước khi response accepted tới. Handle đến muộn vẫn phải được cancel nếu cờ hủy đã bật.''')
    r.code('''goal.pose.header.frame_id = "map"
goal.pose.header.stamp = node.get_clock().now().to_msg()
goal.pose.pose.position.x = target["x"]
goal.pose.pose.position.y = target["y"]
goal.pose.pose.orientation.z = sin(target["yaw"] / 2)
goal.pose.pose.orientation.w = cos(target["yaw"] / 2)
future = action_client.send_goal_async(goal, feedback_callback=... )''')
    r.heading('9.2. Tiêu chí chuyển sang chặng tiếp theo')
    r.paragraphs('''Kết quả action khác STATUS_SUCCEEDED làm dừng cả tuyến. Với status=4, node đọc TF map→base_link và tính sai số Euclid so với goal. Nếu không đọc được localization hoặc sai số lớn hơn 0,4 m, ứng dụng không tuyên bố hoàn thành. Chỉ khi hợp lệ mới thêm region_id vào completed, tăng index và gửi goal kế tiếp.

Nav2 có bộ goal checker riêng với tolerance vị trí 0,25 m và yaw 0,25 rad trong cấu hình. Kiểm tra ứng dụng bổ sung chỉ đo sai số x–y, không phải một phép chứng nhận độc lập về yaw. Hai tầng kiểm tra có vai trò khác nhau; không nên diễn giải ngưỡng 0,4 m của ứng dụng thành tolerance điều khiển thực tế của Nav2.''')

    r.page('10. ĐỊNH VỊ, TRÁNH VẬT CẢN VÀ ĐIỀU KIỆN SẴN SÀNG')
    r.heading('10.1. Liên kết map – odom – base_link')
    r.paragraphs('''AMCL kết hợp bản đồ tĩnh, LiDAR và odometry để cung cấp biến đổi map→odom. Phần odometry/robot cung cấp odom→base_link. Node nhận lệnh chỉ sử dụng pose từ chuỗi TF này trong quá trình điều hướng. Cùng một cặp số x, y nhưng khác frame không có cùng ý nghĩa; đó là lý do cần đặt frame_id=map và kiểm tra TF còn mới.

Đối với world maze vừa khởi động, prepare_sim.py dùng vị trí ground truth đọc từ simulator để đặt initial pose và gọi Undock chính thức. Đoạn chuẩn bị không teleport robot. Việc dùng ground truth chỉ giới hạn ở initial pose của map và world đã biết cùng gốc, cùng phần đối chiếu kết quả. Các goal Nav2 sau đó không dùng ground truth như một bộ điều khiển thay AMCL.''')
    r.heading('10.2. Các kiểm tra trước và trong hành trình')
    r.table(['Điều kiện','Giới hạn đang triển khai','Xử lý khi không đạt'],[
        ['Action server','NavigateToPose phải sẵn sàng','Từ chối trước khi bắt đầu tuyến.'],
        ['/clock','Có timestamp mới trong 4 s thực','Không bắt đầu / hủy khi đang chạy.'],
        ['/scan','Có timestamp mới trong 4 s thực','Không tiếp tục khi LiDAR dừng cập nhật.'],
        ['/dock_status','Mới trong 6 s; is_docked=false','Yêu cầu undock / kiểm tra dữ liệu.'],
        ['TF map→base_link','Không quá 2 s theo ROS time','Chưa xem localization là hợp lệ.'],
        ['Goal timeout','240 s theo đồng hồ thực mỗi goal','Yêu cầu hủy và dừng phần còn lại.'],
        ['Lệnh mới khi bận','Không tự thay route đang chạy','Thông báo bận, cần dừng trước khi đổi.']
    ],caption='Các điều kiện vận hành và watchdog.')
    r.paragraphs('''Watchdog dùng steady clock/monotonic cho thời hạn thực, tránh việc Gazebo pause cũng làm timeout đứng yên. Với /clock và /scan, node kiểm tra timestamp có thay đổi, không chỉ kiểm tra có nhận lại cùng một message. Thông tin cũ được phát lặp không được coi là dữ liệu cảm biến mới.

Tránh vật cản do Nav2 thực hiện thông qua costmap và LiDAR. Cấu hình hiện tại có bán kính robot 0,19 m, inflation_radius 0,45 m, controller_frequency 20 Hz và max_vel_x 0,26 m/s. Các số này là thông số cấu hình, không phải vận tốc đo trung bình của lượt demo. Khi đổi world/map hoặc thêm vật cản động cần kiểm tra lại planner, costmap và khả năng đi qua lối hẹp.''')

    r.page('11. GIAO DIỆN, TOPIC ROS VÀ DỮ LIỆU HIỂN THỊ')
    r.figure(ROOT/'artifacts/live_navigation.png','Ảnh dashboard lấy trong lúc robot thực sự đang đi đến C bằng Nav2.',16.7)
    r.paragraphs('''Bên trái là bản đồ semantic và đường màu cam lấy từ /plan. Ký hiệu robot dựa vào pose TF nhận từ node điều hướng. Bên phải hiển thị trạng thái action, transcript, nguồn âm thanh trong demo, route, các chặng đã đến và khoảng cách feedback. Vì vậy ảnh giao diện vừa giúp thao tác vừa giúp kiểm tra câu lệnh đã được hiểu theo nghĩa nào.

Ảnh này là ảnh chụp trạng thái đang chạy, không phải bằng chứng giọng người thật. Dòng “âm thanh tổng hợp → Vosk → Nav2 thật” được giữ trên giao diện khi kiểm thử bằng WAV. Nút câu mẫu mang nguồn TEXT; không được dùng thay cho một lượt nhận giọng nói trong thống kê ASR.''')
    r.table(['Topic / action','Kiểu dữ liệu','Vai trò'],[
        ['/voice_nav/command','std_msgs/String (JSON hoặc text)','Đầu vào text/source/confidence.'],
        ['/voice_nav/status','std_msgs/String JSON','Trạng thái, route, completed, pose, lỗi readiness.'],
        ['/voice_nav/regions','visualization_msgs/MarkerArray','Viền/tên vùng để RViz hiển thị.'],
        ['/navigate_to_pose','nav2_msgs/action/NavigateToPose','Goal, feedback, result và cancel.'],
        ['/plan','nav_msgs/Path','Đường kế hoạch từ Nav2, không do dashboard tự tạo.'],
        ['/scan; /clock; /dock_status','LaserScan; Clock; DockStatus','Dữ liệu kiểm tra hệ thống.'],
        ['TF map→base_link','tf2 transform','Pose hiện tại để vẽ và hậu kiểm đích.']
    ],caption='Các giao tiếp chính của ứng dụng.',size=9.6)

    r.page('12. QUY TRÌNH CÀI ĐẶT VÀ CHẠY THỬ')
    r.heading('12.1. Chuẩn bị workspace và thư viện')
    r.paragraphs('''Đặt hai package trong thư mục src của cùng workspace. Source ROS trước khi build; sau build cần source install/setup.bash để tìm package vừa tạo. Môi trường voice sử dụng Python 3.10 hệ thống với system-site-packages. Model Vosk tải một lần, nằm ngoài repository để không làm bộ nộp chứa weights và venv.''')
    r.code('''source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select \\
  turtlebot4_slam_nav turtlebot4_voice_nav
python3 -m venv --system-site-packages .venv-tb4-voice
.venv-tb4-voice/bin/python -m pip install \\
  -r src/turtlebot4_voice_nav/requirements-voice.txt
.venv-tb4-voice/bin/python \\
  src/turtlebot4_voice_nav/tools/download_voice_model.py''')
    r.heading('12.2. Ba terminal vận hành')
    r.code('''# Terminal 1: khởi động maze + robot + localization + Nav2
bash src/turtlebot4_voice_nav/scripts/start_simulation.sh

# Terminal 2: source ROS, workspace và lab_env.bash trước
python3 src/turtlebot4_voice_nav/tools/prepare_sim.py
ros2 run turtlebot4_voice_nav voice_navigator --ros-args \\
  -p use_sim_time:=true

# Terminal 3: giao diện và micro tiếng Việt
bash src/turtlebot4_voice_nav/scripts/run_dashboard.sh --micro''')
    r.paragraphs('''Trên máy thử nghiệm Intel, overlay Ogre2 và giới hạn camera mô phỏng 5 Hz được dùng để LiDAR hoạt động đúng và giảm tải hiển thị. Các helper tạo overlay trong cache người dùng, không sửa trực tiếp /opt/ros. Mọi terminal cần cùng cấu hình ROS_DOMAIN_ID/RMW và cùng môi trường DDS; terminal khác domain sẽ khiến giao diện không tìm thấy node dù các tiến trình đều đang chạy.

Sau khi khởi động, kiểm tra bản đồ/laser có khớp vị trí robot, action server sẵn sàng, robot đã undock và dashboard không báo lỗi readiness. Không mở thêm teleop hay gửi goal chuột trong lúc đang chạy thử tuyến giọng nói, vì hai nguồn điều khiển đồng thời làm khó xác định nguyên nhân kết quả.

Launcher trong IDE hỗ trợ --bai 7 để mở dashboard và --bai 1/2/3 để mở bài trước. Dashboard không tự khởi động một robot 2D thay thế nếu Nav2 chưa có. Người sử dụng phải giữ simulator và node điều hướng hoạt động, hoặc làm lại các bước chuẩn bị khi vừa khởi động máy.''')

    r.page('13. THIẾT KẾ THỬ NGHIỆM VÀ NGUỒN BẰNG CHỨNG')
    r.heading('13.1. Phân tầng kiểm chứng')
    r.table(['Tầng','Đầu vào và hệ thống','Khẳng định được','Không suy ra được'],[
        ['Logic core','Map/alias/câu text; unittest','Tọa độ, đích, tuyến, tên lạ được xử lý theo luật','Độ chính xác giọng người; chất lượng điều khiển.'],
        ['Decoder','Recognizer giả và WAV cache','UTF-8, giữ partial, chốt câu, [unk]','Tỷ lệ đúng trong môi trường ồn bất kỳ.'],
        ['ROS action mock','Server NavigateToPose giả, domain 79','Thứ tự, reject, abort, hủy đến muộn','Robot đã chạy ngoài simulator.'],
        ['Tích hợp Gazebo','WAV tổng hợp → Vosk → Nav2/TurtleBot 4','Tuyến và chuyển động mô phỏng theo action thực','Độ chính xác ASR trên giọng sinh viên.'],
        ['Giọng người thật','Micro trực tiếp của người dùng','Chưa thu thập bộ đánh giá định lượng','Không báo cáo một tỷ lệ thành công giả.']
    ],caption='Phạm vi của từng loại bằng chứng.',size=9.3)
    r.paragraphs('''Trong demo tích hợp, các WAV tiếng Việt được tạo bằng Google TTS từ câu mẫu chung, sau đó cache vào artifacts/asr_google. Bước nhận dạng sử dụng Vosk offline trên dữ liệu PCM thật của WAV. Chương trình chỉ gửi lệnh nếu transcript được giải mã phù hợp route kỳ vọng; không có cơ chế lấy câu dự định nói thay cho kết quả nhận dạng sai.

Thứ tự chạy tích hợp là: đến A; đến phòng thí nghiệm B; từ A đến B; đến hành lang C; thử vùng D. Việc chạy lệnh đến B trước lệnh A→B tạo điều kiện robot đang ở nơi khác A. Điều này giúp kiểm tra đúng yêu cầu phải đến A trước khi quay lại B.

Trước lượt ghi tích hợp đã có một lượt text smoke test đưa robot đến gần A. Vì vậy goal A đầu lượt tích hợp có thể được action chấp nhận gần như ngay lập tức do robot đã nằm trong tolerance. Báo cáo giữ nguyên dữ liệu và giải thích tình huống, không dùng thời gian rất ngắn đó làm bằng chứng robot đi quãng đường dài với tốc độ cao.''')
    r.heading('13.2. Các file làm căn cứ')
    r.paragraphs('''integration_results.json lưu câu nói, transcript, confidence, thứ tự goal, pose cuối, telemetry và kết quả toàn lượt. validation.json tổng hợp các điều kiện đã đối chiếu. navigation.jsonl ghi sự kiện node. video_provenance.json ghi nguồn hình/âm thanh và thời điểm đặt các clip âm thanh tổng hợp; video_validation.json ghi số khung đã giải mã. Các log test tách theo nhóm để tránh gộp thử server giả thành thành tích Gazebo.''')

    r.page('14. BẢNG KIỂM THỬ TỰ ĐỘNG CHI TIẾT')
    r.table(['Nhóm / STT','Nội dung kiểm tra','Kỳ vọng'],[
        ['Core 01','Ba câu lệnh bắt buộc','A; A→B; B đúng.'],
        ['Core 02','Tuyến mở rộng A qua C đến B','Giữ thứ tự A,C,B.'],
        ['Core 03','Vùng lạ ở bất cứ vị trí nào','Từ chối toàn tuyến.'],
        ['Core 04','Phủ định, [unk], thiếu động từ','Không NAVIGATE.'],
        ['Core 05','Cancel và cách đọc bê/xê','Đúng ý định/alias.'],
        ['Core 06','Hậu tố lạ sau tên phòng','Không cắt bỏ từ lạ.'],
        ['Core 07','Pixel/world với origin quay','Round-trip đúng ô.'],
        ['Core 08','Goal free/clearance/đúng label','Mọi vùng đạt ràng buộc.'],
        ['Core 09','Vùng trống bị tường ngăn','Không lan qua tường.'],
        ['Core 10','Unknown, ngoài map, NaN','Goal không hợp lệ.'],
        ['Decoder 01','Grammar giữ Unicode tiếng Việt','Không chứa token \\u giả.'],
        ['Decoder 02','Partial tuyến đang nói dở','Chưa gửi movement.'],
        ['Decoder 03','Hết 8 giây; giữ [unk]','Có final; không xóa từ lạ.'],
        ['Action 01','Đang nơi khác, lệnh A→B','Gửi A rồi B.'],
        ['Action 02','Tuyến chứa khu vực lạ','Không có goal gửi.'],
        ['Action 03','Server reject goal đầu','Không gửi chặng sau.'],
        ['Action 04','Server abort goal đầu','Không gửi chặng sau.'],
        ['Action 05','Hủy trước response accepted','Cancel handle đến muộn.'],
        ['Action 06','Mic confidence thấp','Không gửi goal di chuyển.']
    ],caption='19 phương thức kiểm thử đã đạt theo log.',size=9.4)
    r.paragraphs('''Các kiểm tra action được thực hiện với server giả trong một ROS domain riêng để không gửi lệnh tới robot đang dùng demo. Server giả là công cụ điều khiển có chủ đích các kết quả khó tái hiện, chẳng hạn reject hoặc acceptance đến muộn. Kết quả này bổ sung cho lượt Gazebo nhưng không chứng minh robot đã tránh một vật cản cụ thể khi xảy ra lỗi đó.''')

    r.page('15. KẾT QUẢ ASR VÀ BÀI HỌC TỪ MẪU NHẬN SAI')
    r.table(['Câu nói tổng hợp','Transcript cuối','Confidence','Route / kết quả'],[
        [row['spoken'],row['transcript'],f"{row['confidence']:.4f}", ' → '.join(row['route']) or row['kind']] for row in asr
    ],caption='Kết quả Vosk trên năm WAV Google TTS đã cache.',size=9.2)
    r.paragraphs('''Bốn câu chỉ định các vùng hợp lệ được giải mã thành đúng tuyến; câu “Đi đến khu vực D” được giải mã tên vùng thành “đê” và parser trả UNKNOWN_REGION. Cách viết transcript không cần giống hoàn toàn câu dự định theo dấu câu/hoa thường; tiêu chí điều hướng là ý định và thứ tự vùng sau chuẩn hóa.

Năm mẫu trên không tạo thành một đánh giá thống kê độ chính xác tiếng Việt. Chúng có cùng nguồn giọng tổng hợp, ít đa dạng về người nói, khoảng cách micro và tiếng nền. Không thể kết luận hệ thống đạt 100% trên giọng người thật chỉ từ năm câu đã chuẩn bị. Báo cáo không tính WER tổng quát vì chưa có tập dữ liệu người nói đa dạng và protocol tương ứng.''')
    r.heading('15.1. Kết quả eSpeak ban đầu và ý nghĩa')
    espeak=read('artifacts/asr/asr_results.json')
    r.table(['Câu mẫu eSpeak','Transcript nhận được','Ý định/tuyến thực nhận'],[
        [row['spoken'],row['transcript'],(' → '.join(row['route']) or row['kind'])] for row in espeak
    ],caption='Các kết quả lỗi ban đầu vẫn được lưu, không dùng thay kết quả cuối.',size=9)
    r.paragraphs('''Một số mẫu eSpeak bị nhận thành ý định khác, kể cả trường hợp tuyến dự kiến A→B lại thành B→C với confidence khá cao. Điều này cho thấy giọng tổng hợp có cách phát âm không phù hợp vẫn làm hệ thống sai, và confidence không phải bảo đảm ngữ nghĩa. Ở ca mẫu vùng lạ, việc parser không tạo route chỉ chứng minh không phát lệnh trong mẫu đó, chưa đồng nghĩa đã nhận đúng chữ D.

Ngoài kiểm tra bằng hàm giải mã WAV, công cụ validate_live_decoder.py đưa chính các WAV qua make_recognizer và UtteranceDecoder dùng bởi microphone. Bước này phát hiện khác biệt mã hóa grammar: cần ensure_ascii=False để Vosk nhận từ tiếng Việt UTF-8 thực thay vì chuỗi ký tự \\uXXXX. Kiểm thử hồi quy riêng đã được thêm để tránh tái xuất hiện lỗi này.''')

    r.page('16. KẾT QUẢ ĐIỀU HƯỚNG GAZEBO THEO TỪNG GOAL')
    r.table(['Lần','Goal / câu lệnh','Pose cuối TF (x,y)','Sai số (m)','Thời gian thực (s)'],[
        [i+1, f"{row['region']} – "+('trong tuyến A→B' if i in (2,3) else 'đến lab' if i==1 else 'hành lang' if i==4 else 'đã ở gần A'),
         f"({row['finish'][0]:.4f}; {row['finish'][1]:.4f})",f"{row['error_m']:.6f}",f"{row['duration_s']:.3f}"]
        for i,row in enumerate(m['goals'])
    ],caption='Năm goal thực Nav2 được kiểm tra trong lượt tích hợp.',size=9.5)
    r.figure(FIGURES/'goal_durations.png','Thời gian từ GOAL_SENT đến GOAL_SUCCEEDED theo wall_time; goal A đầu đã ở gần đích.',16.5)
    r.heading('16.1. Diễn giải các chặng')
    r.paragraphs('''Goal A đầu tiên hoàn thành trong khoảng 0,314 s vì robot đã nằm gần A sau lượt text smoke test trước đó. Pose bắt đầu khoảng (−1,9334; −2,7721), gần goal (−2; −3). Vì vậy không dùng kết quả này để suy ra tốc độ di chuyển hoặc thời gian đi từ gốc bản đồ tới A.

Lệnh đến phòng thí nghiệm đưa robot từ gần A sang B trong khoảng 43,218 s. Tiếp theo, khi robot đang gần B tại (1,7997; −3,1429), lệnh “Di chuyển từ khu vực A đến khu vực B” thực hiện hai goal: đến A mất 52,164 s rồi về B mất 40,573 s. Đây là bằng chứng trực tiếp cho quy tắc không bỏ qua vùng nguồn.

Chặng đến hành lang C bắt đầu gần B và kết thúc gần (−1,8998; 3,7860), mất 82,825 s theo đồng hồ thực. Tổng thời gian action của năm goal khoảng 219,095 s; tổng lượt tích hợp 229,939 s còn bao gồm xử lý lệnh và khoảng dừng giữa các lượt. Không nhầm các thời gian này với thời gian simulation khi simulator chạy chậm hơn thời gian thực.''')

    r.page('17. PHÂN TÍCH SAI SỐ, QUỸ ĐẠO VÀ HAZARD')
    r.figure(FIGURES/'arrival_errors.png','Sai số vị trí cuối từng goal và các ngưỡng cấu hình/hậu kiểm.',16.5)
    r.table(['Đại lượng','Giá trị','Cách diễn giải'],[
        ['Sai số nhỏ nhất',f"{m['min_error_m']:.6f} m",'Goal A trong tuyến A→B.'],
        ['Sai số lớn nhất',f"{m['max_error_m']:.6f} m",'Không vượt 0,25 m trong năm mẫu x–y ghi nhận.'],
        ['Trung bình',f"{m['mean_error_m']:.6f} m",'Trung bình số học của năm sai số Euclid.'],
        ['Trung vị',f"{m['median_error_m']:.6f} m",'Giá trị giữa khi sắp xếp.'],
        ['RMSE',f"{m['rmse_m']:.6f} m",'Căn trung bình bình phương các sai số.'],
        ['Độ lệch chuẩn tổng thể',f"{m['std_population_m']:.6f} m",'Mô tả năm mẫu, không phải ước lượng độ tin cậy của mọi lượt.'],
        ['Khoảng cách tâm–tường nhỏ nhất','0,419981 m','Theo 440 mẫu ground truth và box vách maze.']
    ],caption='Thống kê tính lại từ dữ liệu action/TF và đối chiếu Gazebo.',size=9.8)
    r.paragraphs('''Sai số ở đây được tính bằng sqrt((x_TF−x_goal)²+(y_TF−y_goal)²) tại thời điểm đọc sau action. Nó bao gồm ảnh hưởng tolerance của goal checker, sai số localization và thời điểm lấy mẫu; không phải chỉ là sai số cơ khí. Không có đủ dữ liệu để tách riêng từng nguồn sai số hoặc suy ra phân phối xác suất trên nhiều môi trường.

Không ghi nhận sự kiện BUMP, CLIFF, STALL hoặc WHEEL_DROP trong dữ liệu hazard của lượt này. Tuy nhiên, không có hazard không đồng nghĩa một chứng minh toán học không va chạm. Khoảng cách 0,420 m là khoảng cách nhỏ nhất tại các mẫu đã lấy đối với các box vách được xét; chưa đánh giá liên tục mọi thời điểm, mọi mesh hoặc vật cản động chưa xuất hiện trong lượt thử.''')

    r.page('18. ĐỐI CHIẾU QUỸ ĐẠO VÀ XỬ LÝ KHU VỰC LẠ')
    r.figure(FIGURES/'recorded_trajectory.png','Quỹ đạo ground truth đã lấy mẫu trong lượt tích hợp, chồng lên bản đồ cùng frame đã chuẩn bị.',12.3)
    r.paragraphs('''Đồ thị sử dụng đúng các mẫu lưu trong integration_results.json, không phải đường nội suy được tạo để thay kết quả Nav2. Các lần đi qua A và B có thể chồng lên nhau nên một đường màu đơn không thể hiện riêng thứ tự; thứ tự được đối chiếu thêm bằng chuỗi GOAL_SENT/GOAL_SUCCEEDED trong log.

Sau khi hoàn thành chặng C, câu “Đi đến khu vực D” được Vosk giải mã thành “đi đến khu vực đê”. Vì alias này không thuộc A/B/C, parser trả UNKNOWN_REGION. Kiểm thử kiểm tra có sự kiện REJECTED và không có GOAL_SENT cho yêu cầu đó. Robot không được phép chọn một khu vực gần âm để thay cho vùng không tồn tại.

Ảnh/video của phiên kiểm thử cũ có thể vẫn giữ route C và dòng SUCCEEDED của yêu cầu trước bên cạnh thông báo từ chối mới. Source cuối đã chỉnh giao diện/trạng thái ứng dụng để yêu cầu bị từ chối hiển thị REJECTED và xóa route cũ. Cải tiến hiển thị này không thay đổi dữ liệu chuyển động hoặc biến yêu cầu D thành một goal hợp lệ.''')

    r.page('19. LỖI ĐÃ GẶP, CÁCH KHẮC PHỤC VÀ KIỂM SOÁT CHẤT LƯỢNG')
    r.table(['Vấn đề','Nguyên nhân / rủi ro','Cách xử lý trong bản hiện tại'],[
        ['Trùng tên self.handle','rclpy.Node có thuộc tính handle nội bộ','Đổi thành goal_handle, giữ riêng action handle.'],
        ['Tiếng Việt biến thành \\uXXXX','Grammar JSON dùng escape Unicode khi Vosk cần từ UTF-8','Dùng ensure_ascii=False; test grammar và pipeline runtime.'],
        ['Partial bị giữ lâu','Tiếng nền làm thiếu endpoint','Hiển thị partial; chốt cửa sổ tối đa 8 s.'],
        ['Partial mất phần đích sau','Gửi câu khi người dùng chưa nói hết','Không phát movement từ partial ổn định.'],
        ['Vùng D nhận nhầm B','Grammar nhỏ thiên về tên hợp lệ gần âm','Bổ sung cách đọc đê/dê và giữ từ lạ; kiểm tra semantic.'],
        ['Nhận lại dữ liệu cũ','Có message nhưng timestamp không tiến','Theo dõi clock/scan có timestamp mới.'],
        ['Hủy trước accepted','Goal handle chưa tồn tại khi người dùng Stop','Ghi cờ hủy; cancel ngay khi handle đến.'],
        ['set -u khi source ROS','Script setup đọc biến tùy chọn chưa đặt','Launcher không bật nounset trước source.'],
        ['Tải hiển thị mô phỏng','Cạnh tranh tài nguyên GPU/CPU','Overlay Ogre2 và camera 5 Hz trên máy thử.']
    ],caption='Các vấn đề kỹ thuật và biện pháp đã áp dụng.',size=9.5)
    r.paragraphs('''Các lỗi được xử lý theo chuỗi tái hiện → sửa ở lớp liên quan → chạy kiểm tra phù hợp. Ví dụ, lỗi UTF-8 không thể được phát hiện chỉ bằng test parser trên chuỗi Python đã đúng; cần đưa WAV qua đúng hàm tạo recognizer mà microphone sử dụng. Tương tự, một server action giả rất hữu ích để tái hiện acceptance đến muộn, nhưng phải giữ nó trong domain riêng để không làm nhiễu Nav2 đang hoạt động.

Không xóa dấu vết kết quả ASR eSpeak sai để trình bày một tỷ lệ hoàn hảo. Báo cáo chỉ dùng các log thực tế để tính số liệu, ghi rõ loại đầu vào và các thay đổi sau lượt quay. Điều này giúp người đọc kiểm tra được lời khẳng định nào dựa trên test logic, lời khẳng định nào dựa trên robot mô phỏng và phần nào chưa được đo.''')

    r.page('20. GIỚI HẠN, ĐÁNH GIÁ VÀ HƯỚNG PHÁT TRIỂN')
    r.heading('20.1. Giới hạn hiện tại')
    r.paragraphs('''Phân vùng dựa vào hạt giống chức năng nên cần người dùng hiểu bản đồ để đặt seed và tên phù hợp. Ranh giới geodesic không nhất thiết trùng cửa/phòng vật lý. Nếu muốn tự nhận phòng, cần bổ sung tiêu chí hình thái, phát hiện cửa hẹp, watershed hoặc mô hình phân loại không gian và đánh giá bằng dữ liệu gán nhãn độc lập.

Bộ parser hỗ trợ một miền câu nhỏ và so khớp alias chặt. Cách này giảm suy đoán sai nhưng làm các câu diễn đạt khác mẫu dễ bị từ chối. ASR cũng chưa được đánh giá trên nhiều giọng, tốc độ nói, khoảng cách micro và tiếng ồn. Điểm tin cậy cao không loại trừ việc nhận sai một chữ cái; ứng dụng thực tế cần xem xét bước xác nhận cho các lệnh ảnh hưởng lớn.

Thử nghiệm mới dùng một world maze với một bản đồ đã lưu và năm goal của một lượt tích hợp. Không có cơ sở để suy rộng tỷ lệ thành công sang mọi bản đồ, mọi mật độ vật cản hoặc robot vật lý. Độ an toàn khi gặp người đi ngang, vật cản động và thay đổi môi trường còn cần các kịch bản riêng.''')
    r.heading('20.2. Các mở rộng đề xuất')
    r.bullet('Cho phép người dùng chọn/vẽ vùng trực tiếp trên bản đồ, xem khoảng trống của goal và lưu phiên bản seed/metadata trước khi chạy.')
    r.bullet('Tự phát hiện lối hẹp và vùng phòng bằng morphology/watershed; giữ nhãn chức năng là lớp dữ liệu tách khỏi thuật toán hình học.')
    r.bullet('Bổ sung bước robot đọc lại tuyến bằng tiếng nói và yêu cầu xác nhận khi nhiều tên vùng gần âm hoặc confidence không chắc chắn.')
    r.bullet('Thu bộ dữ liệu người thật có ground-truth transcript để tính WER, đúng ý định, đúng tuyến, false activation và độ trễ từ hết câu đến gửi goal.')
    r.bullet('Thử nhiều điểm xuất phát và vật cản động; đánh giá khoảng cách tối thiểu, số recovery, độ dài đường và thời gian theo simulation lẫn wall clock.')
    r.bullet('Lưu version bản đồ, YAML transform và config cùng mã băm; tái kiểm tra đích tự động khi có thay đổi dữ liệu hoặc phần mềm.')
    r.heading('20.3. Kết luận kỹ thuật')
    r.paragraphs('''Hệ thống đã nối được bản đồ có nhãn với lệnh tiếng Việt và thực thi route tuần tự bằng Nav2 trong TurtleBot 4 Simulation. Kết quả đáng chú ý là tuyến A→B vẫn đi qua A khi robot đang ở B, vùng không tồn tại không tạo goal, và các điều kiện lỗi có đường hủy/dừng rõ ràng. Các kết quả được lưu bằng log và video để có thể đối chiếu; phần giọng người thật và công bố repository public vẫn là hạng mục cần hoàn tất khi có dữ liệu/kết nối tương ứng.''')

    r.page('21. HƯỚNG DẪN QUAY DEMO VÀ DANH MỤC NỘP BÀI')
    r.heading('21.1. Kịch bản quay lại bằng giọng người thật')
    r.table(['Bước','Thao tác','Thông tin cần thấy trên video'],[
        ['1','Mở Gazebo, RViz/dashboard; kiểm tra robot undock','Map đúng world, robot và LiDAR/localization sẵn sàng.'],
        ['2','Bật micro và nói Đi đến khu vực A','Giọng người, transcript, route A và quá trình robot tới đích.'],
        ['3','Nói Đi đến phòng thí nghiệm','Alias tên semantic ánh xạ B và robot di chuyển.'],
        ['4','Khi đang B, nói Di chuyển từ A đến B','Robot đi A trước, thông báo đã đến A, sau đó B.'],
        ['5','Nói Đi đến hành lang','Route C và pose cuối gần goal C.'],
        ['6','Nói Đi đến khu vực D','Transcript vùng lạ, REJECTED, không có chuyển động mới.'],
        ['7','Có thể thử Stop giữa đường','Thấy yêu cầu cancel và robot dừng; gửi lại lệnh mới để chạy.']
    ],caption='Kịch bản bổ sung bằng người nói thật.',size=9.5)
    r.paragraphs('''Nút ghi video nội bộ ghi hình dashboard và câu ASR nhưng không thu bản âm thanh microphone của người dùng. Nếu cần đáp ứng video thể hiện rõ người ra lệnh bằng giọng nói, dùng trình quay màn hình có bật micro và đưa Gazebo/RViz cùng dashboard vào khung. Nên bắt đầu quay trước khi phát câu lệnh, giữ nguyên thứ tự sự kiện và không cắt một đoạn nhận sai thành đoạn nhận đúng.

Video hiện có DEMO_BAI07.mp4 dài 264,2 s dùng hình điều hướng thật và các clip Google TTS đã cache để nghe lại đầu vào thử nghiệm. Thời gian chuyển động được giữ nguyên, không tăng tốc để làm robot có vẻ hoàn thành nhanh hơn. video_provenance.json ghi lịch đặt audio; dòng chữ trên video nêu rõ nguồn âm thanh tổng hợp.''')
    r.heading('21.2. Nội dung nộp và trạng thái công bố')
    r.bullet('Source: hai package ROS trong repository local đã commit; kèm README và lệnh cài đặt/build để tái hiện.')
    r.bullet('Bản đồ: map.pgm, map.yaml, segmented_map.png, region_labels.npy, regions.json và region_seeds.yaml.')
    r.bullet('Bằng chứng: video MP4, WAV mẫu, log điều hướng, số liệu kiểm chứng và log 19 test.')
    r.bullet('Báo cáo: PDF tóm tắt 2 trang đúng đề, bản Word chi tiết bổ sung để chỉnh sửa/thuyết trình.')
    r.paragraphs('''Ở thời điểm lập báo cáo, chưa xác nhận có repository GitHub public đã push thành công. Commit local không phải đường dẫn GitHub. Khi có kết nối GitHub cần tạo/push repository public, kiểm tra truy cập từ bên ngoài và cập nhật URL vào trang bìa hoặc phụ lục; không điền một URL giả để hoàn thiện hình thức.''')

    r.page('22. PHỤ LỤC: LỆNH TÁI HIỆN, TRÍCH LOG VÀ TÀI LIỆU')
    r.heading('22.1. Lệnh kiểm tra và truy vết')
    r.code('''source /opt/ros/humble/setup.bash
source install/setup.bash
export PYTHONPATH="$PWD/src/turtlebot4_voice_nav:$PYTHONPATH"
python3 -m unittest discover -s src/turtlebot4_voice_nav/test \\
  -p test_core.py -v
python3 -m unittest discover -s src/turtlebot4_voice_nav/test \\
  -p test_speech_decoder.py -v
ROS_DOMAIN_ID=79 ROS_LOCALHOST_ONLY=1 \\
  RMW_IMPLEMENTATION=rmw_fastrtps_cpp \\
  python3 src/turtlebot4_voice_nav/test/test_action_flow.py
.venv-tb4-voice/bin/python \\
  src/turtlebot4_voice_nav/tools/validate_live_decoder.py
python3 src/turtlebot4_voice_nav/tools/validate_evidence.py''')
    r.heading('22.2. Mẫu cấu trúc sự kiện log')
    r.code('''{"event":"GOAL_SUCCEEDED", "command":"di chuyển từ khu vực a đến khu vực bê",
 "source":"SYNTHETIC_AUDIO", "route":["A","B"], "region_id":"A",
 "pose":[-1.865997,-3.120332,0.265405], "error_m":0.180101,
 "action_status":4}

{"event":"REJECTED", "command":"đi đến khu vực đê",
 "message":"Không có khu vực ...", "source":"SYNTHETIC_AUDIO"}''')
    r.p('Các ví dụ trên được rút gọn trường và số chữ số để trình bày; file JSON/JSONL gốc là nguồn đối chiếu đầy đủ, không dùng đoạn rút gọn này để tính lại thống kê.')
    r.heading('22.3. Tài liệu tham khảo và dữ liệu gốc')
    refs=[
        '[1] TurtleBot 4 User Manual – Simulator: https://turtlebot.github.io/turtlebot4-user-manual/software/turtlebot4_simulator.html',
        '[2] Nav2 Humble – định nghĩa action trên máy: /opt/ros/humble/share/nav2_msgs/action/NavigateToPose.action.',
        '[3] Vosk Models – model small-vn-0.4: https://alphacephei.com/vosk/models.',
        '[4] gTTS – tạo câu mẫu tổng hợp: https://gtts.readthedocs.io/en/latest/module.html.',
        '[5] Mã nguồn thực nghiệm: segmentation.py, commands.py, navigator.py, speech.py, dashboard.py; cấu hình nav2.yaml và region_seeds.yaml.',
        '[6] Dữ liệu đối chiếu: integration_results.json, validation.json, live_decoder_validation.json, asr_google/asr_results.json và ba file log test.',
        '[7] Nguồn video: DEMO_BAI07.mp4, video_provenance.json và video_validation.json; ngày thử 07/11/2026.'
    ]
    for ref in refs:
        paragraph=r.p(ref);paragraph.paragraph_format.space_after=Pt(5)
        for run in paragraph.runs: run.font.size=Pt(10)

    # Fill the contents page with bookmark-based page references, excluding front matter.
    main_contents=[item for item in r.contents if re.match(r'^\d+\.',item[0])]
    for paragraph,(title,bookmark) in zip(toc_paragraphs,main_contents):
        paragraph.paragraph_format.space_after=Pt(4)
        paragraph.paragraph_format.line_spacing=1.0
        paragraph.paragraph_format.tab_stops.add_tab_stop(Cm(16.3))
        run=paragraph.add_run(title+'\t');run.font.size=Pt(10)
        r.field(paragraph, f'PAGEREF {bookmark} \\h')
    output=DOCS/'BAO_CAO_BAI07_CHI_TIET.docx'
    r.doc.save(output)
    print(output)
    print('Chapters:',len(main_contents),'Figures:',r.fig_number,'Tables:',len(r.doc.tables),'Numbered tables:',r.table_number)
    print('Paragraphs:',len(r.doc.paragraphs),'Words:',sum(len(p.text.split()) for p in r.doc.paragraphs))
    return output


if __name__ == '__main__': build_report()
