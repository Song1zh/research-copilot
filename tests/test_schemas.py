from pydantic import ValidationError
from schemas import StructuredAnswer


def test_valid_schema():
    data = {
        "topic": "FastAPI",
        "summary": "FastAPI 是一个现代 Python Web 框架。",
        "key_points": ["高性能", "类型提示友好", "自动生成接口文档"],
        "citations": [
            {
                "title": "FastAPI Official Documentation",
                "source": "FastAPI",
                "url": "https://fastapi.tiangolo.com/"
            }
        ],
        "uncertainty": None
    }
    obj = StructuredAnswer(**data)
    print("合法数据解析成功：")
    print(obj.model_dump())

def test_invalid_schema():
    bad_data = {
        "topic": "FastAPI",
        "summary": "FastAPI 是一个现代 Python Web 框架。",
        "key_points": "高性能, 类型提示友好",  # 错误：应为 list[str]
        "citations": [
            {
                "title": "FastAPI Official Documentation",
                "source": "FastAPI"
            }
        ],
        "uncertainty": None
    }

    try:
        StructuredAnswer(**bad_data)
    except ValidationError as e:
        print("非法数据解析失败，错误如下：")
        print(e)


if __name__ == "__main__":
    test_valid_schema()
    print("\n" + "=" * 50 + "\n")
    test_invalid_schema()