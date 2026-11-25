// Power Query (M) for table 'Repeat'.
let
    RetailRows = #table({"purchasers", "returning"}, {
        {"5850", "4200"}
    })
in Table.TransformColumnTypes(RetailRows, {{"purchasers", Int64.Type}, {"returning", Int64.Type}}, "en-GB")
