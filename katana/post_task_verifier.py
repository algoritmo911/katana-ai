import json
import os
import datetime

# Placeholder for actual verification logic based on task_id
# This could involve checking databases, APIs, file systems, etc.
# For now, we'll simulate based on task_id naming.

# Define expected outputs for dummy tasks for simulation purposes
# In a real system, this might come from a configuration or task definition
DUMMY_TASK_EXPECTATIONS = {
    "create_config_file": {
        "type": "file_check",
        "filepath": "config.env",
        "success_message": "Configuration file 'config.env' found.",
        "failure_reason": "отсутствует файл config.env",
        "failure_fix": "создать его или выполнить ./scripts/setup.sh",
    },
    "run_migrations": {
        "type": "log_check",  # Placeholder, actual log check logic needed
        "log_file": "/tmp/migrations.log",
        "success_keyword": "Migrations completed successfully",
        "failure_reason": "ошибки в логах миграции",
        "failure_fix": "проверить /tmp/migrations.log и исправить ошибки в скриптах миграции",
    },
    "start_server": {
        "type": "port_check",  # Placeholder, actual port check logic needed
        "port": 8080,
        "failure_reason": "сервер не запустился на порту 8080",
        "failure_fix": "проверить логи сервера и убедиться, что порт 8080 не занят",
    },
    "successful_task": {
        "type": "generic_success",  # A task that is always successful for testing
        "failure_reason": "эта задача не должна падать",  # Should not be used
        "failure_fix": "проверить логику задачи successful_task",
    },
}

DEFAULT_FAILURE_REASON = "неизвестная ошибка во время выполнения задачи."
DEFAULT_FAILURE_FIX = "проверить логи задачи и системные ресурсы."


def check_unit_tests(task_id: str) -> tuple[bool, str]:
    """
    Placeholder for running unit tests related to a task.
    Returns (success_status, message)
    """
    # Simulate test run: in reality, this would trigger a test runner
    print(f"Simulating unit tests for task: {task_id}...")
    if task_id == "task_with_failing_tests":
        return False, "Модульные тесты провалены: TestFeatureX.test_new_functionality"
    return True, "Все модульные тесты пройдены."


def check_service_port(task_id: str, port: int) -> tuple[bool, str]:
    """
    Placeholder for checking if a service is listening on a specific port.
    Returns (success_status, message)
    """
    # Simulate port check: in reality, this would try to connect to the port
    print(f"Simulating port check for task: {task_id} on port {port}...")
    if (
        port == 8080 and task_id == "start_server_fails_port_check"
    ):  # Simulate failure for a specific case
        return False, f"Порт {port} неактивен."
    # For other 'start_server' tasks, assume success for now if not the specific failing one
    if "start_server" in task_id:
        return True, f"Сервис успешно слушает порт {port}."
    return True, f"Проверка порта для задачи {task_id} не применима или прошла успешно."


def check_logs_for_errors(
    task_id: str, log_file: str, success_keyword: str = None
) -> tuple[bool, str]:
    """
    Placeholder for checking logs for error messages or success keywords.
    Returns (success_status, message)
    """
    print(f"Simulating log check for task: {task_id} in file {log_file}...")
    if (
        not os.path.exists(log_file) and "create" not in task_id
    ):  # if log file itself is missing (and not a creation task)
        return False, f"Файл логов {log_file} не найден."

    # Simulate reading log file
    # In a real scenario, you'd read the file content:
    # with open(log_file, 'r') as f:
    #     content = f.read()
    # if "ERROR" in content: return False, "Обнаружены ошибки в логах."
    # if success_keyword and success_keyword in content: return True, "Ключевое слово успеха найдено в логах."

    if task_id == "task_with_log_errors":
        return (
            False,
            f"Обнаружены ошибки в {log_file}: 'FATAL: Database connection failed'",
        )
        # if success_keyword and task_id == "run_migrations_success_keyword_missing": # This was too specific
        return (
            False,
            f"Ожидаемое ключевое слово '{success_keyword}' не найдено в {log_file}.",
        )

    # Simulate reading log file content for keyword check
    if os.path.exists(log_file) and success_keyword:
        try:
            with open(log_file, "r", encoding="utf-8") as f:
                content = f.read()
            if success_keyword not in content:
                return (
                    False,
                    f"Ожидаемое ключевое слово '{success_keyword}' не найдено в {log_file}.",
                )
            # else, keyword found, continue to other checks or return True if this is the only check
        except Exception as e:
            return False, f"Ошибка чтения файла логов {log_file}: {e}"
    elif (
        not os.path.exists(log_file) and success_keyword
    ):  # If keyword is expected but log file doesn't exist
        return (
            False,
            f"Файл логов {log_file} не найден, но ожидалось ключевое слово '{success_keyword}'.",
        )

    return (
        True,
        f"Проверка логов для {log_file} прошла успешно (или не требует специфического ключевого слова).",
    )


def verify_task(task_id: str) -> dict:
    """
    Verifies the completion of a given task.
    Returns a dictionary with verification status, reason, and fix suggestion.
    """
    timestamp = datetime.datetime.now().isoformat()
    expectation = DUMMY_TASK_EXPECTATIONS.get(task_id)

    if not expectation:  # Generic task not in our predefined list
        # For unknown tasks, we could try a generic check or default to success/needs-manual-check
        # For now, let's assume it's a success if not explicitly defined to fail.
        # Or, more realistically, it might mean verifier doesn't know how to check it.
        # Let's default to a "cannot verify" state or a generic success for now.
        # To make it testable, let's make "unknown_task" fail.
        if task_id == "unknown_task_force_fail":
            return {
                "task_id": task_id,
                "status": "failure",
                "timestamp": timestamp,
                "reason": f"Задача '{task_id}' неизвестна системе верификации и не может быть проверена автоматически.",
                "fix_suggestion": "Убедитесь, что задача определена в DUMMY_TASK_EXPECTATIONS или реализуйте для нее логику проверки.",
                "verification_method": "unknown",
            }
        return {  # Default to success for other unknown tasks for now
            "task_id": task_id,
            "status": "success",
            "timestamp": timestamp,
            "reason": f"Задача '{task_id}' не имеет специфических критериев проверки, предполагается успешной.",
            "fix_suggestion": "Если задача требует проверки, добавьте ее в DUMMY_TASK_EXPECTATIONS.",
            "verification_method": "none",
        }

    verification_method = expectation["type"]
    result = {
        "task_id": task_id,
        "timestamp": timestamp,
        "verification_method": verification_method,
    }

    if verification_method == "file_check":
        filepath = expectation["filepath"]
        if os.path.exists(filepath):
            result["status"] = "success"
            # result["message"] = expectation.get("success_message", f"File '{filepath}' exists.")
        else:
            result["status"] = "failure"
            result["reason"] = expectation["failure_reason"]
            result["fix_suggestion"] = expectation["failure_fix"]
    elif verification_method == "log_check":
        log_file = expectation["log_file"]
        success_keyword = expectation.get("success_keyword")
        # Basic simulation: if the task is "run_migrations", assume it creates and writes to its log
        # This part needs more robust simulation or actual file interaction in tests
        if task_id == "run_migrations" and not os.path.exists(
            log_file
        ):  # Simulate log creation for this specific task
            with open(log_file, "w") as f:
                f.write("Simulated log entry.\n")
                if success_keyword:
                    f.write(success_keyword + "\n")

        success, message = check_logs_for_errors(task_id, log_file, success_keyword)
        if success:
            result["status"] = "success"
            # result["message"] = message
        else:
            result["status"] = "failure"
            result["reason"] = expectation.get("failure_reason", message)
            result["fix_suggestion"] = expectation.get(
                "failure_fix", "Проверьте детали в сообщении об ошибке логов."
            )
    elif verification_method == "port_check":
        port = expectation["port"]
        success, message = check_service_port(task_id, port)
        if success:
            result["status"] = "success"
            # result["message"] = message
        else:
            result["status"] = "failure"
            result["reason"] = expectation.get("failure_reason", message)
            result["fix_suggestion"] = expectation.get(
                "failure_fix", "Проверьте логи сервиса и доступность порта."
            )
    elif verification_method == "generic_success":
        result["status"] = "success"
        # result["message"] = f"Task '{task_id}' is generically considered successful."
    else:
        result["status"] = "error"  # Error in verification definition
        result["reason"] = (
            f"Неизвестный метод верификации '{verification_method}' для задачи '{task_id}'."
        )
        result["fix_suggestion"] = (
            "Обновите DUMMY_TASK_EXPECTATIONS с корректным типом проверки."
        )

    if result["status"] == "success" and "success_message" in expectation:
        result["message"] = expectation["success_message"]
    elif result["status"] == "success":  # Generic success message if not specified
        result["message"] = (
            f"Задача '{task_id}' успешно верифицирована методом '{verification_method}'."
        )

    # Fallback for reason/fix if not set during a failure
    if result.get("status") == "failure":
        if "reason" not in result or not result["reason"]:
            result["reason"] = DEFAULT_FAILURE_REASON
        if "fix_suggestion" not in result or not result["fix_suggestion"]:
            result["fix_suggestion"] = DEFAULT_FAILURE_FIX

    return result


def write_katana_result(result: dict, filepath: str = "katana_result.json"):
    """
    Writes the verification result to a JSON file.
    """
    try:
        with open(filepath, "w") as f:
            json.dump(result, f, indent=2, ensure_ascii=False)
        print(f"Результат верификации записан в {filepath}")
    except IOError as e:
        print(f"Ошибка записи результата верификации в {filepath}: {e}")


if __name__ == "__main__":
    # Example Usage (for direct testing of this module)

    # --- Test "create_config_file" ---
    # Simulate file missing
    if os.path.exists(DUMMY_TASK_EXPECTATIONS["create_config_file"]["filepath"]):
        os.remove(DUMMY_TASK_EXPECTATIONS["create_config_file"]["filepath"])
    verification1 = verify_task("create_config_file")
    print(f"\nVerification for 'create_config_file' (file missing):")
    print(json.dumps(verification1, indent=2, ensure_ascii=False))
    write_katana_result(verification1, "katana_result_config_fail.json")

    # Simulate file existing
    with open(DUMMY_TASK_EXPECTATIONS["create_config_file"]["filepath"], "w") as f:
        f.write("DUMMY_ENV_VAR=example\n")
    verification2 = verify_task("create_config_file")
    print(f"\nVerification for 'create_config_file' (file exists):")
    print(json.dumps(verification2, indent=2, ensure_ascii=False))
    write_katana_result(verification2, "katana_result_config_success.json")
    if os.path.exists(
        DUMMY_TASK_EXPECTATIONS["create_config_file"]["filepath"]
    ):  # Clean up
        os.remove(DUMMY_TASK_EXPECTATIONS["create_config_file"]["filepath"])

    # --- Test "run_migrations" (simulated log check) ---
    # Simulate log file with errors (or missing success keyword)
    # For this test, we'll rely on the internal logic of verify_task and check_logs_for_errors
    # which uses task_id to simulate specific log content scenarios.
    # To make it more concrete, let's ensure the log file is absent first for a specific sub-test
    migrations_log_path = DUMMY_TASK_EXPECTATIONS["run_migrations"]["log_file"]
    if os.path.exists(migrations_log_path):
        os.remove(migrations_log_path)

    # This task ID will internally simulate log check success
    verification3 = verify_task("run_migrations")  # This will create and pass
    print(f"\nVerification for 'run_migrations' (simulated success):")
    print(json.dumps(verification3, indent=2, ensure_ascii=False))
    write_katana_result(verification3, "katana_result_migrations_success.json")
    if os.path.exists(migrations_log_path):  # Clean up
        os.remove(migrations_log_path)

    # To test failure, we'd need a task_id that check_logs_for_errors handles as failure.
    # For example, "task_with_log_errors" (if it were in DUMMY_TASK_EXPECTATIONS with type log_check)
    # Or "run_migrations_success_keyword_missing"
    # Let's add a temporary expectation for this test
    DUMMY_TASK_EXPECTATIONS["run_migrations_fail_test"] = {
        "type": "log_check",
        "log_file": "/tmp/migrations_fail.log",  # Use a different log for this test
        "success_keyword": "Migrations completed successfully",  # This keyword will be missing
        "failure_reason": "ключевое слово успеха не найдено в логах миграции.",
        "failure_fix": "проверить /tmp/migrations_fail.log.",
    }
    # Create a dummy log file without the success keyword
    with open(
        DUMMY_TASK_EXPECTATIONS["run_migrations_fail_test"]["log_file"], "w"
    ) as f:
        f.write(
            "Some migration activity...\nERROR: Something went slightly wrong but not a showstopper.\n"
        )

    verification_migrations_fail = verify_task("run_migrations_fail_test")
    print(
        f"\nVerification for 'run_migrations_fail_test' (simulated failure - keyword missing):"
    )
    print(json.dumps(verification_migrations_fail, indent=2, ensure_ascii=False))
    write_katana_result(
        verification_migrations_fail, "katana_result_migrations_fail.json"
    )
    if os.path.exists(
        DUMMY_TASK_EXPECTATIONS["run_migrations_fail_test"]["log_file"]
    ):  # Clean up
        os.remove(DUMMY_TASK_EXPECTATIONS["run_migrations_fail_test"]["log_file"])
    del DUMMY_TASK_EXPECTATIONS["run_migrations_fail_test"]  # remove temp expectation

    # --- Test "successful_task" ---
    verification4 = verify_task("successful_task")
    print(f"\nVerification for 'successful_task':")
    print(json.dumps(verification4, indent=2, ensure_ascii=False))
    write_katana_result(verification4, "katana_result_generic_success.json")

    # --- Test an unknown task that defaults to success ---
    verification5 = verify_task("some_other_task_id_123")
    print(
        f"\nVerification for 'some_other_task_id_123' (unknown, defaults to success):"
    )
    print(json.dumps(verification5, indent=2, ensure_ascii=False))
    write_katana_result(verification5, "katana_result_unknown_success.json")

    # --- Test an unknown task that is forced to fail ---
    verification6 = verify_task("unknown_task_force_fail")
    print(f"\nVerification for 'unknown_task_force_fail' (unknown, forced to fail):")
    print(json.dumps(verification6, indent=2, ensure_ascii=False))
    write_katana_result(verification6, "katana_result_unknown_fail.json")

    print(
        "\nNote: For 'log_check' and 'port_check', current implementation is highly simulated."
    )
    print("Actual checks would involve file I/O and network operations.")

    # Clean up dummy log file that might have been created by "run_migrations"
    if os.path.exists(DUMMY_TASK_EXPECTATIONS["run_migrations"]["log_file"]):
        os.remove(DUMMY_TASK_EXPECTATIONS["run_migrations"]["log_file"])
