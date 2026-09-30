from app.pii import scrub_text


def test_scrub_email() -> None:
    out = scrub_text("Email me at student@vinuni.edu.vn")
    assert "student@" not in out
    assert "REDACTED_EMAIL" in out


def test_scrub_common_vietnamese_phone_formats() -> None:
    phone_numbers = (
        "0901234567",
        "090 123 4567",
        "090.123.4567",
        "090-123-4567",
        "+84 90 123 4567",
    )

    for phone_number in phone_numbers:
        out = scrub_text(f"Contact: {phone_number}")
        assert phone_number not in out
        assert "REDACTED_PHONE_VN" in out


def test_scrub_cccd() -> None:
    cccd_numbers = (
        "001234567890",
        "079123456789",
        "038099012345",
    )
    for cccd in cccd_numbers:
        out = scrub_text(f"CCCD của tôi là {cccd}")
        assert cccd not in out
        assert "REDACTED_CCCD" in out


def test_scrub_credit_card() -> None:
    card_numbers = (
        "4111 1111 1111 1111",
        "4111-1111-1111-1111",
        "4111111111111111",
        "5500 0000 0000 0004",
        "5500-0000-0000-0004",
    )
    for card in card_numbers:
        out = scrub_text(f"Card number is {card}")
        assert card not in out
        assert "REDACTED_CREDIT_CARD" in out


def test_scrub_passport() -> None:
    passports = (
        "B1234567",
        "C9876543",
    )
    for passport in passports:
        out = scrub_text(f"Số hộ chiếu là {passport}")
        assert passport not in out
        assert "REDACTED_PASSPORT" in out


def test_scrub_combined_text() -> None:
    text = (
        "Email: student@vinuni.edu.vn, Phone: 0987654321, "
        "CCCD: 001234567890, Card: 4111-1111-1111-1111"
    )
    out = scrub_text(text)
    assert "student@vinuni.edu.vn" not in out
    assert "0987654321" not in out
    assert "001234567890" not in out
    assert "4111-1111-1111-1111" not in out
    assert "REDACTED_EMAIL" in out
    assert "REDACTED_PHONE_VN" in out
    assert "REDACTED_CCCD" in out
    assert "REDACTED_CREDIT_CARD" in out
