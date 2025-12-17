package com.arcabank.keybind;

import com.arcabank.ArcaBankClient;
import com.arcabank.screen.MainMenuScreen;
import com.arcabank.screen.QuickPriceScreen;
import com.arcabank.screen.ReportTradeScreen;
import net.fabricmc.fabric.api.client.keybinding.v1.KeyBindingHelper;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.option.KeyBinding;
import net.minecraft.client.util.InputUtil;
import org.lwjgl.glfw.GLFW;

/**
 * Keybinding registration and handling for Arca Bank
 */
public class KeyBindings {
    private static final String CATEGORY = "arcabank.key.category";

    // Open main menu (default: K)
    public static KeyBinding openMenu;

    // Quick price check (default: P)
    public static KeyBinding quickPrice;

    // Report trade (default: R + Alt)
    public static KeyBinding reportTrade;

    /**
     * Register all keybindings
     */
    public static void register() {
        openMenu = KeyBindingHelper.registerKeyBinding(new KeyBinding(
                "arcabank.key.open_menu",
                InputUtil.Type.KEYSYM,
                GLFW.GLFW_KEY_K,
                CATEGORY
        ));

        quickPrice = KeyBindingHelper.registerKeyBinding(new KeyBinding(
                "arcabank.key.quick_price",
                InputUtil.Type.KEYSYM,
                GLFW.GLFW_KEY_P,
                CATEGORY
        ));

        reportTrade = KeyBindingHelper.registerKeyBinding(new KeyBinding(
                "arcabank.key.report_trade",
                InputUtil.Type.KEYSYM,
                GLFW.GLFW_KEY_J,
                CATEGORY
        ));

        ArcaBankClient.LOGGER.info("Keybindings registered");
    }

    /**
     * Handle keybindings on client tick
     */
    public static void onEndTick(MinecraftClient client) {
        // Don't process if in screen or no world
        if (client.player == null || client.world == null) {
            return;
        }

        // Check for key presses
        while (openMenu.wasPressed()) {
            openMainMenu(client);
        }

        while (quickPrice.wasPressed()) {
            openQuickPrice(client);
        }

        while (reportTrade.wasPressed()) {
            openReportTrade(client);
        }
    }

    private static void openMainMenu(MinecraftClient client) {
        ArcaBankClient.LOGGER.debug("Opening main menu");
        client.setScreen(new MainMenuScreen());
    }

    private static void openQuickPrice(MinecraftClient client) {
        ArcaBankClient.LOGGER.debug("Opening quick price check");
        client.setScreen(new QuickPriceScreen(null));
    }

    private static void openReportTrade(MinecraftClient client) {
        ArcaBankClient.LOGGER.debug("Opening trade report screen");
        client.setScreen(new ReportTradeScreen(null));
    }
}
