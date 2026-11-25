// Power Query (M) for table 'Products'.
let
    RetailRows = #table({"product", "product_gross"}, {
        {"Manual (M)", "338788.14"},
        {"REGENCY CAKESTAND 3 TIER (22423)", "324596.2"},
        {"DOTCOM POSTAGE (DOT)", "289981.42"},
        {"CREAM HANGING HEART T-LIGHT HOLDER (85123A)", "255498.3"},
        {"JUMBO BAG RED RETROSPOT (85099B)", "178342.44"},
        {"PARTY BUNTING (47566)", "147399.8"},
        {"ASSORTED COLOUR BIRD ORNAMENT (84879)", "127161.75"},
        {"POSTAGE (POST)", "122899.13"},
        {"PAPER CHAIN KIT 50'S CHRISTMAS (22086)", "110892.53"},
        {"MEDIUM CERAMIC TOP STORAGE JAR (23166)", "81448.21"}
    })
in Table.TransformColumnTypes(RetailRows, {{"product", type text}, {"product_gross", Currency.Type}}, "en-GB")
