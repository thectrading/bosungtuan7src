"""Generate the requested TWO-page PDF with actual validation numbers."""
import json
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.enums import TA_JUSTIFY
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, Table, TableStyle, PageBreak


def main():
    root = Path(__file__).resolve().parents[1]
    validation = json.loads((root/'artifacts/validation.json').read_text())
    results = json.loads((root/'artifacts/integration_results.json').read_text())
    regions = json.loads((root/'maps/regions.json').read_text())['regions']
    pdfmetrics.registerFont(TTFont('DejaVu', '/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf'))
    pdfmetrics.registerFont(TTFont('DejaVuBold', '/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf'))
    pdfmetrics.registerFontFamily('DejaVu', normal='DejaVu', bold='DejaVuBold')
    normal = ParagraphStyle('body', fontName='DejaVu', fontSize=9.2, leading=13.4, spaceAfter=6)
    heading = ParagraphStyle('heading', parent=normal, fontName='DejaVuBold', fontSize=11.1, leading=15, spaceBefore=7, spaceAfter=7, textColor=colors.HexColor('#246b99'))
    title = ParagraphStyle('title', parent=heading, fontSize=16, leading=21, spaceBefore=0, spaceAfter=10)
    tiny = ParagraphStyle('tiny', parent=normal, fontSize=8, leading=11)
    p = lambda value: Paragraph(value, normal)
    h = lambda value: Paragraph(value, heading)
    story = [Paragraph('BÀI THỰC HÀNH 7<br/>Phân vùng bản đồ và điều hướng bằng giọng nói', title),
             p('Ubuntu 22.04 • ROS 2 Humble • TurtleBot 4 Lite • Ignition Fortress • Nav2 • Vosk tiếng Việt'),
             h('1. Phân vùng và gắn nhãn ngữ nghĩa'),
             p('Sử dụng bản đồ Occupancy Grid đã quét bằng SLAM ở world maze. Threshold theo free_thresh/occupied_thresh từ map.yaml; ô chưa biết và vật cản không được điều hướng. Chọn thủ công ba hạt giống chức năng, rồi tự động lan nhãn theo khoảng cách đường đi 4 hướng trên ô free (geodesic Voronoi). Tường chặn lan nhãn; vùng free không nối hạt giống được để chưa gán.'),
             p('Tên Phòng học/Phòng thí nghiệm/Hành lang là nhãn chức năng do người dùng gán trên mê cung, không phải suy luận loại phòng hay watershed tự phát hiện phòng. Kết quả gồm ảnh phân vùng, lưới nhãn và regions.json (ID, tên, alias, goal, biên vùng, diện tích, clearance).'),
             Image(str(root/'maps/segmented_map.png'), width=88*mm, height=88*mm)]
    rows = [[Paragraph(s, tiny) for s in ['ID / Tên', 'Goal x, y, yaw', 'Clearance tĩnh']]]
    for region in regions:
        goal = region['goal']
        rows.append([Paragraph(f"{region['id']} · {region['name']}", tiny),
                     Paragraph(f"{goal['x']:.1f}, {goal['y']:.1f}, {goal['yaw']:.2f}", tiny),
                     Paragraph(f"{region['clearance_m']:.2f} m", tiny)])
    table = Table(rows, colWidths=[68*mm, 62*mm, 40*mm])
    table.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5eff6')),
                               ('GRID', (0, 0), (-1, -1), .4, colors.HexColor('#c7d3dc')),
                               ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BOTTOMPADDING', (0, 0), (-1, -1), 6)]))
    story += [Spacer(1, 6), table, Spacer(1, 6),
              p('Quy đổi tâm ô: x=(col+0,5)·resolution; y=(height−row−0,5)·resolution, sau đó quay theo origin yaw và cộng origin. Goal phải nằm đúng nhãn, known-free, clearance ≥0,32 m; không dùng centroid nằm trên tường. Clearance chỉ là kiểm tra bản đồ tĩnh, không thay tránh vật cản của Nav2.'),
              PageBreak(), h('2. Giọng nói, phân tích lệnh và điều hướng'),
              p('Micro arecord thu PCM 16 kHz; Vosk small-vn chạy offline, confidence từ ASR ≥0,65. Chỉ chốt câu hoàn chỉnh để tránh cắt mất đích sau trong lệnh nhiều chặng; cửa sổ tối đa 8 giây khi tiếng nền làm không có điểm kết thúc. Kết quả [unk] được giữ để từ chối thay vì xóa từ. Thêm cách đọc bê/xê và cả đê/dê để không ép tên vùng lạ về vùng đã biết.'),
              p('Parser chuẩn hóa dấu và khớp toàn bộ tên vùng. “Đi đến khu vực A” → A; “Di chuyển từ khu vực A đến khu vực B” → A rồi B; “Đi đến phòng thí nghiệm” → B. Hỗ trợ mở rộng A → C → B. Bất kỳ vùng không tồn tại trong tuyến đều làm từ chối cả tuyến. “Dừng lại” hủy goal và các chặng còn lại.'),
              p('ROS node gọi action NavigateToPose tuần tự trong frame map, không phát cmd_vel. Chặng sau chỉ gửi khi chặng trước status=4 và sai số TF ≤0,4 m. Kiểm tra simulator, LiDAR, dock và localization trước/trong hành trình; reject/abort/cancel/timeout dừng cả tuyến. Vùng được xuất MarkerArray cho RViz; dashboard hiển thị /plan và pose thật.'),
              h('3. Kết quả kiểm thử thực tế trong simulator')]
    lines = ['19 kiểm tra đạt: 10 core, 3 bộ chốt câu/mã hóa UTF-8, 6 luồng action với server giả trên ROS domain riêng.',
             'Demo end-to-end: WAV tiếng Việt tổng hợp → Vosk thực → parser → Nav2/Gazebo thực. Không thay transcript sai bằng câu kỳ vọng.']
    for line in lines: story.append(p(line))
    table_rows = [[Paragraph(s, tiny) for s in ['Câu đã nhận dạng', 'Tuyến / kết quả']]]
    for command in results['commands']:
        target = ' → '.join(command.get('completed_in_order', [])) or 'Từ chối vùng lạ, không goal'
        table_rows.append([Paragraph(command['transcript'], tiny), Paragraph(target, tiny)])
    table2 = Table(table_rows, colWidths=[108*mm, 62*mm])
    table2.setStyle(TableStyle([('BACKGROUND', (0, 0), (-1, 0), colors.HexColor('#e5eff6')),
                                ('GRID', (0, 0), (-1, -1), .4, colors.HexColor('#c7d3dc')),
                                ('VALIGN', (0, 0), (-1, -1), 'TOP'), ('BOTTOMPADDING', (0, 0), (-1, -1), 5)]))
    story += [table2, Spacer(1, 7),
              p(f"4 tuyến/5 goal thành công; sai số cuối tối đa {validation['max_arrival_error_m']:.3f} m. Khi nhận A → B, robot đang ở B và vẫn đi A trước rồi quay lại B. Không ghi nhận BUMP/CLIFF/STALL/WHEEL_DROP. {validation['sampled_ground_truth_points']} mẫu ground truth chỉ đọc cho khoảng cách tâm robot–tường nhỏ nhất {validation['min_sampled_center_to_maze_wall_m']:.3f} m; đây là kiểm tra lấy mẫu, không phải chứng minh va chạm liên tục."),
              h('4. Giới hạn và nội dung nộp'),
              p('5 mẫu giọng Google TTS được nhận/phân tích đúng ở bộ kiểm tra cuối; mẫu eSpeak ban đầu nhận sai được lưu riêng. Các kết quả này KHÔNG là độ chính xác giọng người thật; cần quay thêm giọng của sinh viên bằng micro. Video đã tạo có nhãn âm thanh tổng hợp, giữ thời gian chuyển động Nav2 thật. Bản đồ là phân vùng chức năng bán tự động; cần khảo sát lại khi thay map/world. Chưa xác nhận GitHub public khi chưa có kết nối đẩy repository.'),
              Paragraph('Tệp: maps/map.{pgm,yaml}, segmented_map.png, regions.json; artifacts/DEMO_BAI07.mp4, integration_results.json, validation.json; source và README kèm hướng dẫn. Tham khảo: turtlebot.github.io/turtlebot4-user-manual; alphacephei.com/vosk/models; action NavigateToPose của Nav2 Humble.', tiny)]
    output = root/'docs/REPORT_BAI07.pdf'
    output.parent.mkdir(exist_ok=True)
    def footer(canvas, document):
        canvas.setFont('DejaVu', 8)
        canvas.setFillColor(colors.HexColor('#6a798b'))
        canvas.drawString(20*mm, 12*mm, 'Bài 7 · TurtleBot 4 / Nav2 · Kết quả thử ngày 07/11/2026')
        canvas.drawRightString(190*mm, 12*mm, str(document.page))
    SimpleDocTemplate(str(output), pagesize=(210*mm, 297*mm), leftMargin=20*mm, rightMargin=20*mm,
                      topMargin=16*mm, bottomMargin=20*mm).build(story, onFirstPage=footer, onLaterPages=footer)
    print(output)


if __name__ == '__main__': main()
