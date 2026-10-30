package ir.ayeneh.app;

import com.getcapacitor.BridgeActivity;
import android.os.Bundle;
import android.webkit.WebView;
import androidx.activity.OnBackPressedCallback;

public class MainActivity extends BridgeActivity {
    @Override
    public void onCreate(Bundle savedInstanceState) {
        registerPlugin(SecureModelPlugin.class);
        super.onCreate(savedInstanceState);
        getOnBackPressedDispatcher().addCallback(this, new OnBackPressedCallback(true) {
            @Override
            public void handleOnBackPressed() {
                if (bridge == null || bridge.getWebView() == null) {
                    finish();
                    return;
                }
                WebView webView = bridge.getWebView();
                webView.evaluateJavascript(
                    "(function(){var close=document.querySelector('[aria-label=\\\"Close navigation\\\"]');" +
                    "var drawer=document.querySelector('.app-sidebar-open');" +
                    "if(drawer && close){close.click();return 'drawer';}return 'route';})()",
                    value -> {
                        if ("\"drawer\"".equals(value)) return;
                        if (webView.canGoBack()) webView.goBack();
                        else finish();
                    }
                );
            }
        });
    }
}
