# Ngữ cảnh hai vòng Full Rounds

Tài liệu ngữ cảnh riêng cho nội dung giới thiệu hai bài thi Meko và Crypto. Không thay thế hướng dẫn kết nối, luật thi hoặc cấu hình kỹ thuật.

## Vòng 1 — Meko Boutique

Meko Boutique chuẩn bị ra mắt bộ sưu tập Thu Đông cùng chương trình hội viên C-Nocturne. Ngay trước ngày mở bán, đội vận hành phát hiện một số dấu hiệu bất thường: hóa đơn của khách có thể bị xem trái phép, quyền lợi hội viên có dấu hiệu bị giả mạo và bản đối soát nội bộ xuất hiện ngoài dự kiến. Các dấu hiệu này khiến cửa hàng đứng trước nguy cơ lộ dữ liệu và mất niềm tin của khách hàng.

Các đội được giao nhiệm vụ kiểm tra hệ thống theo mô hình Attack–Defense. Hãy điều tra những điểm yếu trong các bản sao Meko Boutique của đối thủ để tìm flag, đồng thời bảo vệ cửa hàng của đội mình bằng cách khắc phục lỗ hổng và giữ dịch vụ hoạt động. Năm khu vực cần chú ý là tìm kiếm bộ sưu tập, hóa đơn, tải bản phối, thẻ hội viên và bản xuất dữ liệu vận hành.

## Vòng 2 — Crypto AD

Sau sự cố tại cửa hàng, MekoData phát hiện một thành phần nội bộ lưu các hồ sơ giao dịch nhạy cảm. Thành phần này dựa vào ba dịch vụ mật mã: xác thực chứng thư quản trị, bảo vệ bản sao hồ sơ và ký lệnh mở khóa. Rà soát ban đầu cho thấy các kiểm tra tham số đường cong, cách phản hồi khi giải mã thất bại và việc sử dụng nonce có thể tạo cơ hội để kẻ tấn công đọc hoặc giả mạo dữ liệu.

Các đội tiếp tục nhiệm vụ Attack–Defense trên chính các VM đã dùng ở vòng trước. Hãy phân tích dịch vụ của đối thủ để lấy flag từ các bản ghi được đánh dấu, sau đó gia cố phiên bản của đội mình để chặn khai thác mà vẫn duy trì khả năng phục vụ hợp lệ. Ba mảng điều tra là Curveball, Padding Oracle và ECDSA Nonce.
