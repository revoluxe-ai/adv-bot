from time import sleep


def retry_on_error(max_attempts=10, delay_seconds=3):
    def decorator(func):
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    result = func(*args, **kwargs)
                    return result
                except Exception as e:
                    print(f"Error occurred: {str(e)}")
                    attempts += 1
                    if attempts < max_attempts:
                        print(f"Retrying in {delay_seconds} seconds...")
                        sleep(delay_seconds)
                    else:
                        print(f"Max retry attempts reached. Exiting...")
                        raise

        return wrapper

    return decorator
