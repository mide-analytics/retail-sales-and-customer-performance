// Power Query (M) for table 'Markets'.
let
    RetailRows = #table({"country", "market_gross"}, {
        {"United Kingdom", "16818576.377"},
        {"EIRE", "651426.42"},
        {"Netherlands", "542310.07"},
        {"Germany", "417035.541"},
        {"France", "343161.17"},
        {"Australia", "169283.46"},
        {"Spain", "108016.28"},
        {"Switzerland", "100685.59"},
        {"Sweden", "91631.82"},
        {"Denmark", "68411.79"}
    })
in Table.TransformColumnTypes(RetailRows, {{"country", type text}, {"market_gross", Currency.Type}}, "en-GB")
