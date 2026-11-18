# Round 2 · Crypto AD

Mỗi đội có ba dịch vụ TCP chạy trên VM của mình. Dùng `~/crypto-lab/host_port.txt` để xem địa chỉ và cổng của hai đội còn lại.

| Dịch vụ | Cổng | Mô tả |
| --- | ---: | --- |
| Curveball | 9011 | Chứng chỉ số trên đường cong elliptic P-256 |
| Padding Oracle | 9012 | Tài liệu được mã hóa AES-CBC |
| ECDSA Nonce | 9013 | Chữ ký số ECDSA |

Kết nối trực tiếp tới dịch vụ của đội đích bằng `ncat`:

```bash
ncat <IP_ĐỘI_ĐÍCH> <CỔNG>
```

Ví dụ:

```bash
ncat 10.90.0.12 9011
```

Giao tiếp bằng JSON Lines: gửi một đối tượng JSON trên mỗi dòng và đọc phản hồi JSON tương ứng. Có thể dùng `nc` thay cho `ncat` nếu máy đã cài Netcat.
