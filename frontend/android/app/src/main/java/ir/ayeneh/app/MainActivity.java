package ir.ayeneh.app;

import com.getcapacitor.BridgeActivity;
import android.os.Bundle;
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
                bridge.getWebView().evaluateJavascript(
                    "(function(){var close=document.querySelector('[aria-label=\\\"Close navigation\\\"]');" +
                    "var drawer=document.querySelector('.app-sidebar-open');" +
                    "if(drawer && close){close.click();return 'drawer';}" +
                    "if(location.pathname !== '/' && history.length > 1){history.back();return 'route';}" +
                    "if(location.pathname !== '/'){location.href='/';return 'home';}" +
                    "return 'exit';})()",
                    value -> {
                        if ("\"exit\"".equals(value)) finish();
                    }
                );
            }
        });
    }
}
