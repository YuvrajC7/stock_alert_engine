function doPost(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data = JSON.parse(e.postData.contents);
  
  // 1. SET NICE HEADINGS IF THE SHEET IS EMPTY
  if (sheet.getLastRow() == 0) {
    var headers = ["Ticker", "Status", "Price", "Time"];
    sheet.appendRow(headers);
    var headerRange = sheet.getRange(1, 1, 1, 4);
    headerRange.setFontWeight("bold");
    headerRange.setBackground("#4a86e8"); // Nice blue heading
    headerRange.setFontColor("white");
  }
  
  // Search for the ticker in Column A
  var values = sheet.getDataRange().getValues();
  var rowIndex = -1;
  
  // Start loop at 1 to skip the header row
  for (var i = 1; i < values.length; i++) { 
    if (values[i][0] == data.ticker) {
      rowIndex = i + 1;
      break;
    }
  }
  
  // 2. DETERMINE THE BACKGROUND COLOR
  var bgColor = "#ffffff";
  if (data.status == "BULLISH") {
    bgColor = "#b7e1cd"; // Green
  } else if (data.status == "BEARISH") {
    bgColor = "#f4c7c3"; // Red
  } else if (data.status == "NOTHING YET") {
    bgColor = "#e2e3e5"; // Gray
  }
  
  // If ticker exists, update the row. Otherwise, create a new row!
  if (rowIndex > -1) {
    sheet.getRange(rowIndex, 2).setValue(data.status);
    sheet.getRange(rowIndex, 3).setValue(data.price);
    sheet.getRange(rowIndex, 4).setValue(data.time);
    
    // Apply the color to the Status cell
    sheet.getRange(rowIndex, 2).setBackground(bgColor);
  } else {
    sheet.appendRow([data.ticker, data.status, data.price, data.time]);
    var newRow = sheet.getLastRow();
    
    // Apply the color to the newly created Status cell
    sheet.getRange(newRow, 2).setBackground(bgColor);
  }
  
  // 3. SORT ALL STOCKS IN ASCENDING ORDER (Alphabetical by Ticker)
  if (sheet.getLastRow() > 1) {
    // Get the range of all data EXCEPT the header row
    var sortRange = sheet.getRange(2, 1, sheet.getLastRow() - 1, sheet.getLastColumn());
    sortRange.sort({column: 1, ascending: true});
  }
  
  return ContentService.createTextOutput("Success");
}
