from app.matching.confusables import is_confusable_pair


def test_java_javascript_confusable():
    assert is_confusable_pair("Java", "JavaScript")
    assert is_confusable_pair("javascript", "java")


def test_react_not_confusable_with_itself():
    assert not is_confusable_pair("React", "React.js")


def test_aws_azure_confusable():
    assert is_confusable_pair("AWS", "Azure")


def test_python_ruby_not_confusable():
    assert not is_confusable_pair("Python", "Ruby")
