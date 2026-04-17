// Google Apps Script Code    
// Configuration Variables
const API_KEY = 'YOUR_BOLNA_API_KEY_HERE'; // From Bolna dashboard > Developers
const AGENT_ID = 'YOUR_AGENT_ID_HERE'; // From Bolna agent creation
const FROM_PHONE_NUMBER = '+YOUR_FROM_NUMBER_HERE'; // Bolna-purchased or connected number
const SHEET_NAME = 'Sheet1'; // Your sheet tab name
const API_BASE = 'https://api.bolna.ai';
const BATCH_SIZE = 5; // Max rows to process per run (adjust to stay under 6-min timeout)
const TRIGGER_INTERVAL_MINUTES = 1; // Time between batches (minutes)

// Handles incoming webhook POST requests from Bolna
function doPost(e) {
  try {
    // Log raw payload for debugging
    const rawPayload = e.postData ? e.postData.contents : '{}';
    Logger.log('Raw webhook payload: ' + rawPayload);

    // Parse the incoming JSON payload
    const payload = JSON.parse(rawPayload);

    // Extract id and status
    const id = payload.id;
    const status = payload.status;
    if (!id || !status) {
      throw new Error(`Invalid payload: Missing id (${id}) or status (${status}).`);
    }

    // Prepare call results (include extracted_data, summary, error_message, recipient_data)
    const errorMessage = payload.error_message || '';
    const recipientName = payload.context_details?.recipient_data?.name || '';
    let callResults = {};
    if (payload.extracted_data) callResults.extracted_data = payload.extracted_data;
    if (payload.summary) callResults.summary = payload.summary;
    if (errorMessage) callResults.error_message = errorMessage;
    if (recipientName) callResults.recipient_name = recipientName;
    callResults = JSON.stringify(callResults || 'No results');

    // Access the spreadsheet
    const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
    const data = sheet.getDataRange().getValues();

    // Find the row with matching id (Column C)
    let rowUpdated = false;
    for (let i = 1; i < data.length; i++) {
      if (data[i][2] === id) { // Column C (Execution ID)
        // Update Status (Column D) – append error if present
        const updatedStatus = errorMessage ? `${status} (${errorMessage})` : status;
        sheet.getRange(i + 1, 4).setValue(updatedStatus);

        // Update Call Results (Column E) for final statuses
        const finalStatuses = ['completed', 'failed', 'error', 'canceled', 'stopped', 'balance-low', 'busy', 'no-answer'];
        if (finalStatuses.includes(status)) {
          sheet.getRange(i + 1, 5).setValue(callResults);
        }
        rowUpdated = true;
        break;
      }
    }

    if (!rowUpdated) {
      Logger.log(`No matching row found for id: ${id}`);
    }

    // Return success response to Bolna
    return ContentService.createTextOutput(JSON.stringify({ status: 'success' }))
      .setMimeType(ContentService.MimeType.JSON);
  } catch (error) {
    // Log error and return failure response
    Logger.log('Webhook error: ' + error);
    return ContentService.createTextOutput(JSON.stringify({ status: 'error', message: error.message }))
      .setMimeType(ContentService.MimeType.JSON);
  }
}

// Trigger calls for a batch of unprocessed rows
function triggerBolnaCalls() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  const data = sheet.getDataRange().getValues();
  let processedCount = 0;

  // Loop through rows, process up to BATCH_SIZE
  for (let i = 1; i < data.length && processedCount < BATCH_SIZE; i++) {
    const name = data[i][0]; // Column A (Name)
    const phoneNumber = '+91'+data[i][1]; // Column B (Phone Number)
    const processed = data[i][5]; // Column F (Processed)
    if (!phoneNumber || processed === true) continue; // Skip empty or processed rows

    // Trigger call with user_data
    const payload = {
      agent_id: AGENT_ID,
      recipient_phone_number: phoneNumber,
      from_phone_number: FROM_PHONE_NUMBER,
      user_data: { name: name || 'Unknown' } // Include name in user_data
    };

    const options = {
      method: 'post',
      contentType: 'application/json',
      headers: { Authorization: `Bearer ${API_KEY}` },
      payload: JSON.stringify(payload),
    };

    try {
      const response = UrlFetchApp.fetch(`${API_BASE}/call`, options);
      const result = JSON.parse(response.getContentText());
      const executionId = result.execution_id;

      // Update sheet
      sheet.getRange(i + 1, 3).setValue(executionId); // Execution ID (Column C)
      sheet.getRange(i + 1, 6).setValue(true); // Mark as Processed (Column F)
      processedCount++;
    } catch (error) {
      Logger.log(`Error triggering call for ${phoneNumber}: ${error}`);
      sheet.getRange(i + 1, 4).setValue('error'); // Status (Column D)
      sheet.getRange(i + 1, 6).setValue(true); // Mark as Processed to skip retries
      processedCount++;
    }
  }

  // If more unprocessed rows exist, set up a trigger for the next batch
  if (hasUnprocessedRows(sheet, data)) {
    ScriptApp.newTrigger('triggerBolnaCalls')
      .timeBased()
      .after(TRIGGER_INTERVAL_MINUTES * 60 * 1000) // Convert minutes to milliseconds
      .create();
  }
}

// Check if there are unprocessed rows
function hasUnprocessedRows(sheet, data) {
  for (let i = 1; i < data.length; i++) {
    if (data[i][1] && data[i][5] !== true) { // Has phone number and not processed
      return true;
    }
  }
  return false;
}

// Optional: Polling fallback for rows missing webhook updates
function checkPendingCalls() {
  const sheet = SpreadsheetApp.getActiveSpreadsheet().getSheetByName(SHEET_NAME);
  const data = sheet.getDataRange().getValues();

  for (let i = 1; i < data.length; i++) {
    const executionId = data[i][2]; // Column C
    const status = data[i][3]; // Column D
    if (!executionId || status === 'completed' || status === 'failed' || status === 'error') continue;

    // Poll for status
    const options = {
      method: 'get',
      headers: { Authorization: `Bearer ${API_KEY}` },
    };

    try {
      const response = UrlFetchApp.fetch(`${API_BASE}/executions/${executionId}`, options);
      const result = JSON.parse(response.getContentText());
      const newStatus = result.status;

      // Update sheet
      sheet.getRange(i + 1, 4).setValue(newStatus); // Status (Column D)
      if (newStatus === 'completed') {
        const callResults = JSON.stringify(result.extracted_data || result.summary || 'Call completed');
        sheet.getRange(i + 1, 5).setValue(callResults); // Call Results (Column E)
      }
    } catch (error) {
      Logger.log(`Error polling ${executionId}: ${error}`);
      sheet.getRange(i + 1, 4).setValue('error');
    }
  }

  // Re-schedule polling if pending calls remain
  if (hasPendingCalls(sheet, data)) {
    ScriptApp.newTrigger('checkPendingCalls')
      .timeBased()
      .after(5 * 60 * 1000) // Run every 5 minutes
      .create();
  }
}

// Check if there are pending calls (not completed/failed/error)
function hasPendingCalls(sheet, data) {
  for (let i = 1; i < data.length; i++) {
    const executionId = data[i][2];
    const status = data[i][3];
    if (executionId && status !== 'completed' && status !== 'failed' && status !== 'error') {
      return true;
    }
  }
  return false;
}

// Add a custom menu to trigger manually
function onOpen() {
  SpreadsheetApp.getUi().createMenu('Bolna Helper by Yohita')
    .addItem('Trigger Calls', 'triggerBolnaCalls')
    .addItem('Check Pending Calls', 'checkPendingCalls')
    .addToUi();
}

//end of code
