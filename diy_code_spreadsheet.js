function doPost(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data = JSON.parse(e.postData.contents);
  
  // 1. SET NICE HEADINGS IF THE SHEET IS EMPTY
  if (sheet.getLastRow() == 0) {
    var headers = ["Ticker", "Status", "Price", "Time"];
    sheet.appendRow(headers);
    var headerRange = sheet.getRange(1, 1, 1, 4);
    headerRange.setFontWeight("bold");
    headerRange.setBackground("#4a86e8");
    headerRange.setFontColor("white");
  }
  
  var values = sheet.getDataRange().getValues();
  var rowIndex = -1;
  
  // Find the stock (Start at 1 to skip header)
  for (var i = 1; i < values.length; i++) { 
    if (values[i][0] == data.ticker) {
      rowIndex = i + 1;
      break;
    }
  }
  
  // Set nice background color
  var bgColor = "#ffffff";
  if (data.status == "BULLISH") bgColor = "#b7e1cd"; // Green
  else if (data.status == "BEARISH") bgColor = "#f4c7c3"; // Red

  // Update or append
  if (rowIndex > -1) {
    sheet.getRange(rowIndex, 2).setValue(data.status).setBackground(bgColor);
    sheet.getRange(rowIndex, 3).setValue(data.price);
    sheet.getRange(rowIndex, 4).setValue(data.time); // Update to newest time
  } else {
    sheet.appendRow([data.ticker, data.status, data.price, data.time]);
    sheet.getRange(sheet.getLastRow(), 2).setBackground(bgColor);
  }
  
  // 2. SORT BY TIME (COLUMN 4) IN DECREASING ORDER (Newest on top)
  if (sheet.getLastRow() > 1) {
    var sortRange = sheet.getRange(2, 1, sheet.getLastRow() - 1, sheet.getLastColumn());
    sortRange.sort({column: 4, ascending: false});
  }
  
  return ContentService.createTextOutput("Success");
}
