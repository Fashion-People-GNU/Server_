import datetime


def log_request(request, success=True, error_message=None):
    method = request.method
    url = request.url
    headers = dict(request.headers)
    data = request.get_data(as_text=True)
    ip = request.remote_addr

    message = f"""
    {"==" * 50}
    Request Time: {datetime.datetime.now()}
    Request IP: {ip}
    Request Method: {method}
    Request URL: {url}
    Request Headers: {headers}
    Request Data: {data}
    Success: {success}
    """

    # 요청이 실패한 경우 오류 메시지 추가
    if not success and error_message:
        message += f"Error Message: {error_message}\n"

    # 로그 파일에 기록
    with open('request_log.txt', 'a') as log_file:
        log_file.write(message)
