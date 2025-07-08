from datetime import datetime
from typing import Optional, List, Any
from pydantic import BaseModel, Field

class MessageInput(BaseModel):
    """
    Представление сообщения из MemoryManager для анализа.
    """
    role: str
    content: Any  # Может быть строкой или структурированным JSON
    timestamp: datetime

class SessionData(BaseModel):
    """
    Промежуточное хранение данных сессии.
    """
    session_id: str
    chat_id: str
    start_time: datetime
    end_time: datetime
    messages: List[MessageInput]

class FatigueMetricsOutput(BaseModel):
    """
    Представление рассчитанных метрик усталости.
    """
    timestamp: datetime = Field(default_factory=datetime.utcnow)
    user_id: str # Идентификатор пользователя (например, chat_id)
    session_id: str

    command_frequency_5m: Optional[int] = None
    command_frequency_10m: Optional[int] = None
    command_frequency_1h: Optional[int] = None

    average_reaction_time_sec: Optional[float] = None
    median_reaction_time_sec: Optional[float] = None
    std_reaction_time_sec: Optional[float] = None

    error_rate: Optional[float] = None
    session_duration_min: float
    context_switches: int

    user_bot_message_ratio: Optional[float] = None
    user_bot_ratio_warning: bool = False # Флаг, если соотношение превышает порог

    fatigue_score: Optional[float] = None # Опциональная общая оценка усталоosti

    # Дополнительные поля для отладки или расширенного анализа
    total_messages_in_session: int
    user_messages_in_session: int
    bot_messages_in_session: int

    class Config:
        # Для Pydantic V2, если будут проблемы с datetime, можно использовать from_attributes = True
        # model_config = {"from_attributes": True} # Для Pydantic V2
        # Pydantic V1 uses `orm_mode = True` or `from_orm = True` in some contexts,
        # but for simple datetime objects, it should work fine.
        # json_encoders is good for controlling serialization format.
        json_encoders = {
            datetime: lambda v: v.isoformat() + "Z" # Ensure UTC 'Z' notation
        }
        # arbitrary_types_allowed = True # For Pydantic V1, if direct datetime assignment causes issues


# Пример использования (для проверки)
if __name__ == "__main__":
    # Используем datetime.now(timezone.utc) для явного указания UTC
    from datetime import timezone

    now_utc = datetime.now(timezone.utc)

    msg1 = MessageInput(role="user", content="Hello", timestamp=now_utc)
    msg2 = MessageInput(role="assistant", content="Hi there!", timestamp=now_utc)

    print("MessageInput Example:")
    # Pydantic V2 uses model_dump_json, Pydantic V1 uses .json()
    try:
        print(msg1.model_dump_json(indent=2))
    except AttributeError:
        print(msg1.json(indent=2))


    session_data_example = SessionData(
        session_id="chat123_20230101120000",
        chat_id="chat123",
        start_time=now_utc,
        end_time=now_utc,
        messages=[msg1, msg2]
    )
    print("\nSessionData Example:")
    try:
        print(session_data_example.model_dump_json(indent=2))
    except AttributeError:
        print(session_data_example.json(indent=2))


    fatigue_output_example = FatigueMetricsOutput(
        user_id="user_telegram_12345",
        session_id="chat123_20230101120000",
        command_frequency_5m=10,
        average_reaction_time_sec=15.5,
        error_rate=0.05,
        session_duration_min=30.0,
        context_switches=1,
        user_bot_message_ratio=1.2,
        total_messages_in_session=20,
        user_messages_in_session=11,
        bot_messages_in_session=9,
        timestamp=now_utc # Явно передаем для примера
    )
    print("\nFatigueMetricsOutput Example:")
    try:
        print(fatigue_output_example.model_dump_json(indent=2))
    except AttributeError:
        print(fatigue_output_example.json(indent=2))

    # Проверка работы с datetime по умолчанию
    fatigue_output_default_ts = FatigueMetricsOutput(
        user_id="user_test_002",
        session_id="session_test_002_ts",
        session_duration_min=5.0,
        context_switches=0,
        total_messages_in_session=2,
        user_messages_in_session=1,
        bot_messages_in_session=1
        # timestamp будет сгенерирован автоматически
    )
    print("\nFatigueMetricsOutput with default timestamp:")
    try:
        print(fatigue_output_default_ts.model_dump_json(indent=2))
    except AttributeError:
        print(fatigue_output_default_ts.json(indent=2))

    # Демонстрация того, что default_factory работает
    # print(f"Default timestamp: {fatigue_output_default_ts.timestamp}")
