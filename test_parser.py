from Bot.parsers.pulser_parser import parse_xls_to_json

print("Запуск парсера...")
parse_xls_to_json("Bot/data/prices/pdprice.xls")
print("Готово")