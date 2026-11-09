# Bản đồ kèm package

`map.yaml` + `map.pgm` được lưu từ `/map` của SLAM Toolbox chạy cùng robot TurtleBot 4
Lite trong world maze thật của Gazebo Fortress. Không vẽ occupancy bằng tay hoặc
sao chép map mẫu upstream.

- Resolution: 0.05 m/pixel; kích thước 401×401 pixel; origin khoảng (-10,-10,0).
- Trinary PGM: 254 = free, 0 = occupied, 205 = unknown; YAML free_thresh = 0.196.
- Ước lượng vùng sàn trống đã quan sát: khoảng 76.8%, theo hình học maze và giả định
  frame map/world trùng tại spawn mặc định. Đây không phải chứng nhận bao phủ 100%.
- Vẫn có vùng chưa khảo sát ở phía nam và một phần phía đông bắc; cần tiếp tục khảo
  sát bằng teleop trong video chính thức và lưu lại bản map tốt nhất khi nộp bài.
- Map này được tạo trong kiểm thử bằng lệnh vận tốc; chưa có video chứng minh mapping
  bằng `teleop_twist_keyboard`. Các snapshot tiến trình nằm trong artifacts/mapping_snapshots.

Map đủ dùng cho các vùng goal kiểm thử được ghi trong báo cáo. Khi đổi map, phải
kiểm tra lại localization và từng goal; không giả định log của bản cũ áp dụng cho bản mới.
