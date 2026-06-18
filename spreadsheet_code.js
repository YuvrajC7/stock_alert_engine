function doPost(e) {
  var sheet = SpreadsheetApp.getActiveSpreadsheet().getActiveSheet();
  var data = JSON.parse(e.postData.contents);
  
  // Search for the ticker in Column A
  var values = sheet.getDataRange().getValues();
  var rowIndex = -1;
  
  for (var i = 0; i < values.length; i++) {
    if (values[i][0] == data.ticker) {
      rowIndex = i + 1;
      break;
    }
  }
  
  // If ticker exists, update the row. Otherwise, create a new row!
  if (rowIndex > -1) {
    sheet.getRange(rowIndex, 2).setValue(data.status);
    sheet.getRange(rowIndex, 3).setValue(data.price);
    sheet.getRange(rowIndex, 4).setValue(data.time);
  } else {
    sheet.appendRow([data.ticker, data.status, data.price, data.time]);
  }
  
  return ContentService.createTextOutput("Success");
}
