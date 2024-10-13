package org.electrum.qr;

import java.util.Arrays;

import android.app.Activity;
import android.os.Bundle;
import android.util.Log;
import android.content.Intent;
import android.Manifest;
import android.content.ClipData;
import android.content.ClipDescription;
import android.content.ClipboardManager;
import android.content.Context;
import android.content.pm.PackageManager;
import android.view.View;
import android.view.ViewGroup;
import android.widget.Button;
import android.widget.TextView;
import android.widget.Toast;

import androidx.core.app.ActivityCompat;


import com.journeyapps.barcodescanner.CaptureManager;
import com.journeyapps.barcodescanner.DecoratedBarcodeView;
import com.journeyapps.barcodescanner.ViewfinderView;

// import me.dm7.barcodescanner.zxing.ZXingScannerView;

import com.google.zxing.Result;
import com.google.zxing.BarcodeFormat;

import org.electrum.electrum.res.R; // package set in build.gradle

// public class SimpleScannerActivity extends Activity implements ZXingScannerView.ResultHandler {
public class SimpleScannerActivity extends Activity {
    private static final int MY_PERMISSIONS_CAMERA = 1002;

//     private ZXingScannerView mScannerView = null;
    final String TAG = "org.electrum.SimpleScannerActivity";

    private CaptureManager capture;
    private DecoratedBarcodeView barcodeScannerView;
    private Button switchFlashlightButton;
    private ViewfinderView viewfinderView;

    private boolean mAlreadyRequestedPermissions = false;

    @Override
    public void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.scanner_layout);

        barcodeScannerView = findViewById(R.id.zxing_barcode_scanner);
//         barcodeScannerView.setTorchListener(this);

        // change top text
        Intent intent = getIntent();
        String text = intent.getStringExtra(intent.EXTRA_TEXT);
        TextView hintTextView = (TextView) findViewById(R.id.hint);
        hintTextView.setText(text);

        // bind "paste" button
        Button btn = (Button) findViewById(R.id.paste_btn);
        btn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                ClipboardManager clipboard = (ClipboardManager) getSystemService(Context.CLIPBOARD_SERVICE);
                if (clipboard.hasPrimaryClip()
                        && (clipboard.getPrimaryClipDescription().hasMimeType(ClipDescription.MIMETYPE_TEXT_PLAIN)
                            || clipboard.getPrimaryClipDescription().hasMimeType(ClipDescription.MIMETYPE_TEXT_HTML))) {
                    ClipData.Item item = clipboard.getPrimaryClip().getItemAt(0);
                    String clipboardText = item.getText().toString();
                    // limit size of content. avoid https://developer.android.com/reference/android/os/TransactionTooLargeException.html
                    if (clipboardText.length() >  512 * 1024) {
                        Toast.makeText(SimpleScannerActivity.this, "Clipboard contents too large.", Toast.LENGTH_SHORT).show();
                        return;
                    }
                    SimpleScannerActivity.this.setResultAndClose(clipboardText);
                } else {
                    Toast.makeText(SimpleScannerActivity.this, "Clipboard is empty.", Toast.LENGTH_SHORT).show();
                }
            }
        });

        capture = new CaptureManager(this, barcodeScannerView);
        capture.initializeFromIntent(getIntent(), savedInstanceState);
        capture.setShowMissingCameraPermissionDialog(false);
        capture.decode();

    }

    @Override
    public void onResume() {
        super.onResume();
        capture.onResume();
//         if (this.hasPermission()) {
//             this.startCamera();
//         } else if (!mAlreadyRequestedPermissions) {
//             mAlreadyRequestedPermissions = true;
//             this.requestPermission();
//         }
    }

    @Override
    public void onPause() {
        super.onPause();
        capture.onPause();
//         if (null != mScannerView) {
//             mScannerView.stopCamera();           // Stop camera on pause
//         }
    }

    public void onDestroy() {
        super.onDestroy();
        capture.onDestroy();
    }

//     private void startCamera() {
//         mScannerView = new ZXingScannerView(this);
//         mScannerView.setFormats(Arrays.asList(BarcodeFormat.QR_CODE));
//         ViewGroup contentFrame = (ViewGroup) findViewById(R.id.content_frame);
//         contentFrame.addView(mScannerView);
//         mScannerView.setResultHandler(this);         // Register ourselves as a handler for scan results.
//         mScannerView.startCamera();                  // Start camera on resume
//     }

//     @Override
    public void handleResult(Result rawResult) {
        //resultIntent.putExtra("format", rawResult.getBarcodeFormat().toString());
        this.setResultAndClose(rawResult.getText());
    }

    private void setResultAndClose(String resultText) {
        Intent resultIntent = new Intent();
        resultIntent.putExtra("text", resultText);
        setResult(Activity.RESULT_OK, resultIntent);
        this.finish();
    }

    private boolean hasPermission() {
        return (ActivityCompat.checkSelfPermission(this,
                                                   Manifest.permission.CAMERA)
                == PackageManager.PERMISSION_GRANTED);
    }

    private void requestPermission() {
        ActivityCompat.requestPermissions(this,
                    new String[]{Manifest.permission.CAMERA},
                    MY_PERMISSIONS_CAMERA);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String permissions[], int[] grantResults) {
        capture.onRequestPermissionsResult(requestCode, permissions, grantResults);
//         switch (requestCode) {
//             case MY_PERMISSIONS_CAMERA: {
//                 if (grantResults.length > 0
//                     && grantResults[0] == PackageManager.PERMISSION_GRANTED) {
//                     // permission was granted, yay!
//                     this.startCamera();
//                 } else {
//                     // permission denied
//                     //this.finish();
//                 }
//                 return;
//             }
//         }
    }

}
