# Bài 7 — Phân vùng bản đồ và điều hướng TurtleBot 4 bằng giọng nói

Ubuntu 22.04 · ROS 2 Humble · TurtleBot 4 Lite · Ignition Fortress · Nav2 · Vosk tiếng Việt.

Node `voice_navigator` nhận câu tiếng Việt, phân tích đầy đủ tuyến, kiểm tra
region/đích hợp lệ rồi gửi lần lượt action **NavigateToPose**. Không phát
`cmd_vel`, không dùng vị trí giả và không thay Nav2 bằng hoạt cảnh. Dashboard
hiển thị bản đồ có nhãn, vị trí localization và đường `/plan` của Nav2 thật.

## Bản đồ và phương pháp

Dùng lại map occupancy của world **maze** đã tạo bằng SLAM ở bài trước.
`maps/map.yaml` và `.pgm` là bản đồ gốc. `region_labels.npy`, `regions.json`,
`segmented_map.png` là kết quả phân vùng và gắn nhãn.

| Vùng | Nhãn chức năng | Đích map (m, rad) | Clearance bản đồ tĩnh |
| --- | --- | --- | --- |
| A | Phòng học | −2, −3, 0 | 1.05 m |
| B | Phòng thí nghiệm | 2, −3, 0 | 0.95 m |
| C | Hành lang | −2, 4, π/2 | 1.00 m |

Các tên là **nhãn chức năng do người dùng gán** trên mê cung, không phải nhận
dạng loại phòng. Chọn ba hạt giống bằng YAML; tự động chia các ô free theo
khoảng cách đường đi trên lưới 4 hướng đến hạt giống gần nhất (geodesic Voronoi).
Vách/unknown không được đi xuyên và không mang nhãn. Thành phần free không nối
đến hạt giống được giữ chưa gán. Đây là phương pháp bán tự động phù hợp gợi ý
đề bài; chưa phải watershed phát hiện phòng tự động.

Mỗi goal kiểm tra known-free, thuộc đúng vùng, clearance ≥0.32 m. Clearance
tính distance transform coi cả unknown và mép ảnh là vật cản. Số trên chỉ cho
bản đồ tĩnh; Nav2/LiDAR vẫn kiểm tra vật cản trong lúc chạy.

Quy đổi pixel **tâm ô**, đảo trục y và hỗ trợ origin yaw:
`x_local=(col+0.5)*resolution`, `y_local=(height-row-0.5)*resolution`,
sau đó quay theo yaw và cộng origin từ map.yaml. Không lấy centroid hình học
làm goal nếu nó nằm trên tường/unknown.

Tạo lại kết quả:

```bash
source /opt/ros/humble/setup.bash
export PYTHONPATH="$PWD/src/turtlebot4_voice_nav:$PYTHONPATH"
python3 -m turtlebot4_voice_nav.segmentation \
  --map src/turtlebot4_voice_nav/maps/map.yaml \
  --seeds src/turtlebot4_voice_nav/config/region_seeds.yaml \
  --output src/turtlebot4_voice_nav/maps
```

## Cài đặt và build

Đặt **hai package** `turtlebot4_voice_nav` và `turtlebot4_slam_nav` vào `<workspace>/src`.
Package hỗ trợ cung cấp world launcher/config Nav2 của các bài trước.

```bash
sudo apt install ros-humble-turtlebot4-simulator ros-humble-turtlebot4-navigation \
  ros-humble-navigation2 ros-humble-nav2-bringup ros-humble-rmw-cyclonedds-cpp \
  python3-opencv python3-numpy python3-pil python3-yaml python3-tk \
  python3-colcon-common-extensions python3-venv alsa-utils
source /opt/ros/humble/setup.bash
colcon build --symlink-install --packages-select turtlebot4_slam_nav turtlebot4_voice_nav
python3 -m venv --system-site-packages .venv-tb4-voice
.venv-tb4-voice/bin/python -m pip install -r src/turtlebot4_voice_nav/requirements-voice.txt
.venv-tb4-voice/bin/python src/turtlebot4_voice_nav/tools/download_voice_model.py
```

Venv phải dùng Python 3.10 hệ thống để dùng được `rclpy` apt. Không cần Torch.
Model tiếng Việt nằm trong cache chung `~/.cache/bai01_hri/`; không cần source
Bài 1. Sau cài đặt, nhận dạng giọng nói chạy offline, không gửi âm thanh lên dịch vụ.

Trên máy Intel hiện tại cần overlay Ogre2 để LiDAR chính xác:

```bash
python3 src/turtlebot4_slam_nav/scripts/prepare_ogre2_overlay.py
python3 src/turtlebot4_slam_nav/scripts/prepare_camera_overlay.py --rate 5
```

Không sửa `/opt/ros`; các overlay ở cache người dùng. Mọi terminal phải dùng cùng môi trường:

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
source src/turtlebot4_slam_nav/scripts/lab_env.bash
```

## Chạy simulator, Nav2 và giọng nói

Terminal 1, từ workspace:

```bash
bash src/turtlebot4_voice_nav/scripts/start_simulation.sh
```

Terminal 2, source môi trường như trên rồi chuẩn bị localization/undock **chỉ trong
simulator maze vừa khởi động**:

```bash
python3 src/turtlebot4_voice_nav/tools/prepare_sim.py
ros2 run turtlebot4_voice_nav voice_navigator --ros-args -p use_sim_time:=true \
  -p log_file:="$PWD/src/turtlebot4_voice_nav/artifacts/navigation.jsonl"
```

`prepare_sim.py` dùng ground truth **chỉ đọc** làm initial pose cho map maze cùng
gốc world và gọi action Undock chính thức. Không dời robot/teleport, không dùng
ground truth để điều khiển các goal. Khi dùng map khác cần đặt initial pose đúng
trong RViz; không áp dụng script này cho robot thật.

Terminal 3:

```bash
bash src/turtlebot4_voice_nav/scripts/run_dashboard.sh --micro
```

Trên máy hiện tại, launcher IDE cũng mở được dashboard:
`python3 /home/chuc/thuchanhtuongtacnguoi.6 --bai 7 --micro`.
Simulator và node Nav2 cần đang chạy; dashboard không tự tạo robot mô phỏng giả
khi mất ROS. Bản đồ hiển thị vùng được tô màu và robot từ TF map→base_link.
RViz có thể thêm MarkerArray `/voice_nav/regions` để thấy viền/tên vùng.

## Câu lệnh và quy tắc

- **“Đi đến khu vực A.”** → A.
- **“Di chuyển từ khu vực A đến khu vực B.”** → A rồi B, kể cả đang ở C hoặc B.
- **“Đi đến phòng thí nghiệm.”** → B.
- **“Đi đến hành lang.”** → C.
- **“Đi từ phòng A qua hành lang C rồi đến phòng B.”** → A → C → B.
- **“Dừng lại” / “Hủy điều hướng”** → cancel goal hiện tại và phần còn lại.
- **“Đi đến khu vực D/Z”** → báo không tồn tại, không gửi bất kỳ goal nào.

Alias ID không dấu và cách đọc `bê`, `xê` được hỗ trợ. Parser phải khớp toàn bộ
từng tên vùng; đoạn không biết ở giữa tuyến làm từ chối **cả tuyến**. Không bỏ
qua tên lạ rồi vẫn chạy các chặng còn lại. Tối đa 8 chặng.

Khi nói, giữ câu rõ và ngừng khoảng một giây cuối câu. Chỉ chốt lệnh di chuyển
từ kết quả ASR cuối, tránh gửi tuyến chưa nói hết. Sau tối đa 8 giây âm thanh,
chốt cửa sổ để không treo vì tiếng nền; nên nói các lệnh ngắn trong ví dụ.
Confidence microphone <0.65 bị loại; giữ nguyên `[unk]` để parser từ chối.
Không tự xóa từ không nhận ra thành câu có vẻ hợp lệ. Stop có thể được xử lý sớm.

Nút câu mẫu/ô nhập là **TEXT**, không được ghi thành bằng chứng nhận giọng nói.
Khi đang chạy, lệnh mới bị từ chối cho tới khi dừng hoặc hoàn thành.
Nav2 reject/abort/timeout/cancel thì không gửi các chặng sau. Hủy trong lúc
chờ server nhận goal vẫn hủy handle khi nó đến muộn.

## Video và bằng chứng

Nút **Ghi video (F7)** ghi dashboard, câu ASR, tuyến đã hiểu, path và vị trí
thật từ simulator. Video nội bộ không thu mic; có thể quay màn hình kèm mic
để thu người nói và Gazebo/RViz cùng lúc. Esc gửi cancel; đóng dashboard cũng cancel.

Demo tự động trong `artifacts/` ghi rõ **âm thanh tổng hợp**: các câu mẫu tiếng
Việt tạo bằng Google TTS được cache thành WAV, sau đó **Vosk offline giải mã WAV**,
parser lấy đích và Nav2 thực hiện trong TurtleBot4 Gazebo. Không lấy câu dự kiến
thay kết quả ASR, không phát trajectory giả. Đây không thay thế lượt demo giọng
người thật; hãy thử và quay giọng của bạn qua nút micro.

Các WAV được tạo một lần bằng gTTS (tạo mẫu cần mạng, chỉ gửi các câu lệnh chung).
Nhận dạng và điều hướng không cần gTTS/mạng khi đã có WAV. Giọng eSpeak robot
đã nhận sai trong thử nghiệm đầu; giữ kết quả lỗi ở `artifacts/asr/` để không
che kết quả thất bại. Không suy ra độ chính xác giọng người từ bộ mẫu tổng hợp.

## Kiểm thử

Kết quả đã chạy trong phiên này:

- Build thành công ở workspace chính và workspace sạch chứa đúng hai package.
- **19 kiểm tra đạt**: 10 core, 3 chốt câu/mã hóa ASR và 6 action workflow với server giả.
- **4 tuyến / 5 goal Nav2 thật thành công**; tuyến A→B được thử khi robot đang ở B.
- Sai số đến đích 0.180–0.237 m; vùng D không tồn tại bị từ chối, không gửi goal.
- Không có BUMP/CLIFF/STALL/WHEEL_DROP ghi nhận; 440 mẫu ground truth cho khoảng
  cách tâm robot tới vách mê cung nhỏ nhất 0.420 m. Đây là kiểm tra lấy mẫu,
  không phải chứng minh không va chạm liên tục.
- Video `artifacts/DEMO_BAI07.mp4` dài 264.2 giây, giữ nguyên thời gian chuyển động,
  có nhãn nguồn âm thanh tổng hợp. Các clip đầu vào tổng hợp được ghép vào để
  nghe được câu lệnh; xem `video_provenance.json` để biết cách đồng bộ.
- PDF `docs/REPORT_BAI07.pdf` gồm đúng 2 trang A4.
- Báo cáo mở rộng `docs/BAO_CAO_BAI07_CHI_TIET.docx`: 25 trang, 22 chương,
  8 hình và 18 bảng (17 bảng đánh số và 1 bảng thuật ngữ); chỉnh sửa được trong Word. Bản PDF cùng tên dùng để xem
  nhanh bố cục. Trang bìa có ô để điền họ tên/MSSV/lớp/giảng viên.

Log và số liệu: `artifacts/integration_results.json`, `validation.json`,
`asr_google/asr_results.json`, `core_tests.txt`, `action_tests.txt`, `speech_decoder_tests.txt`.
Chưa đánh giá độ chính xác giọng người thật; bản demo dùng WAV giọng tổng hợp
và điều hướng Nav2 thật, không giả là bản thu micro của sinh viên.

```bash
source /opt/ros/humble/setup.bash
source install/setup.bash
export PYTHONPATH="$PWD/src/turtlebot4_voice_nav:$PYTHONPATH"
python3 -m unittest discover -s src/turtlebot4_voice_nav/test -p test_core.py -v
python3 -m unittest discover -s src/turtlebot4_voice_nav/test -p test_speech_decoder.py -v
.venv-tb4-voice/bin/python src/turtlebot4_voice_nav/tools/validate_live_decoder.py
# Action server giả, domain riêng, không chạy robot:
ROS_DOMAIN_ID=79 ROS_LOCALHOST_ONLY=1 RMW_IMPLEMENTATION=rmw_fastrtps_cpp \
  python3 src/turtlebot4_voice_nav/test/test_action_flow.py
```

Core test kiểm tra câu Việt, tuyến nhiều chặng, không bỏ qua khu vực lạ,
phủ định, alias, đổi pixel/world có góc quay, khoảng trống đích và không phân
vùng xuyên tường. Action test dùng server **giả** để kiểm tra thứ tự, reject,
abort, hủy trước acceptance và confidence thấp; không gọi là test Gazebo.

Để chạy lại kiểm thử đầy đủ với WAV cache và simulator đang sẵn sàng:

```bash
.venv-tb4-voice/bin/python src/turtlebot4_voice_nav/tools/integration_demo.py \
  --artifacts "$PWD/src/turtlebot4_voice_nav/artifacts" \
  --regions "$PWD/src/turtlebot4_voice_nav/maps/regions.json"
```

Chương trình chỉ gửi khi ASR thực sự khớp tuyến kỳ vọng, không thay câu sai
bằng câu đúng. Kết quả hoàn thành dựa trên action status=4 và sai số TF ≤0.4 m.
Log gồm confidence, transcript, thứ tự chặng, sai số cuối, ground truth chỉ đọc
và hazard để đối chiếu. PDF 1–2 trang ở `docs/REPORT_BAI07.pdf`.

## Nguồn chính thức

- [TurtleBot 4 Simulator Humble](https://turtlebot.github.io/turtlebot4-user-manual/software/turtlebot4_simulator.html).
- Nav2 action definition: `/opt/ros/humble/share/nav2_msgs/action/NavigateToPose.action`.
- [Vosk models](https://alphacephei.com/vosk/models), [gTTS](https://gtts.readthedocs.io/en/latest/module.html).

Source chuẩn bị cho GitHub public gồm hai package và tài liệu; không gồm venv,
model weights, build/install/log hay dữ liệu tài khoản. Repo/link public phải
được xác nhận sau khi push thành công; không xem commit local là đã public.
