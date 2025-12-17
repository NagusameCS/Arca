package com.arcabank.screen;

import com.arcabank.ArcaBankClient;
import com.arcabank.api.ArcaApiClient;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.text.Text;

/**
 * Main menu screen for Arca Bank
 */
public class MainMenuScreen extends Screen {
    private static final int BUTTON_WIDTH = 150;
    private static final int BUTTON_HEIGHT = 20;
    private static final int BUTTON_SPACING = 24;

    private String balanceText = "Loading...";
    private String marketText = "Loading...";
    private boolean isLoading = true;

    public MainMenuScreen() {
        super(Text.translatable("arcabank.screen.main_title"));
    }

    @Override
    protected void init() {
        super.init();

        int centerX = this.width / 2;
        int startY = this.height / 2 - 40;

        // Price Check Button
        this.addDrawableChild(ButtonWidget.builder(
                Text.translatable("arcabank.button.check_price"),
                button -> this.client.setScreen(new QuickPriceScreen(this))
        ).dimensions(centerX - BUTTON_WIDTH / 2, startY, BUTTON_WIDTH, BUTTON_HEIGHT).build());

        // Report Trade Button
        this.addDrawableChild(ButtonWidget.builder(
                Text.translatable("arcabank.button.report"),
                button -> this.client.setScreen(new ReportTradeScreen(this))
        ).dimensions(centerX - BUTTON_WIDTH / 2, startY + BUTTON_SPACING, BUTTON_WIDTH, BUTTON_HEIGHT).build());

        // My Stats Button
        this.addDrawableChild(ButtonWidget.builder(
                Text.translatable("arcabank.button.my_stats"),
                button -> this.client.setScreen(new MyStatsScreen(this))
        ).dimensions(centerX - BUTTON_WIDTH / 2, startY + BUTTON_SPACING * 2, BUTTON_WIDTH, BUTTON_HEIGHT).build());

        // My Trades Button
        this.addDrawableChild(ButtonWidget.builder(
                Text.translatable("arcabank.button.my_trades"),
                button -> this.client.setScreen(new MyTradesScreen(this))
        ).dimensions(centerX - BUTTON_WIDTH / 2, startY + BUTTON_SPACING * 3, BUTTON_WIDTH, BUTTON_HEIGHT).build());

        // Trending Items Button
        this.addDrawableChild(ButtonWidget.builder(
                Text.translatable("arcabank.button.trending"),
                button -> this.client.setScreen(new TrendingScreen(this))
        ).dimensions(centerX - BUTTON_WIDTH / 2, startY + BUTTON_SPACING * 4, BUTTON_WIDTH, BUTTON_HEIGHT).build());

        // Close Button
        this.addDrawableChild(ButtonWidget.builder(
                Text.translatable("arcabank.button.cancel"),
                button -> this.close()
        ).dimensions(centerX - BUTTON_WIDTH / 2, startY + BUTTON_SPACING * 5 + 10, BUTTON_WIDTH, BUTTON_HEIGHT).build());

        // Load balance and market data
        loadData();
    }

    private void loadData() {
        MinecraftClient client = MinecraftClient.getInstance();
        if (client.player == null) return;

        String uuid = client.player.getUuidAsString();
        ArcaApiClient api = ArcaBankClient.getApiClient();

        // Load balance
        api.getBalance(uuid).thenAccept(response -> {
            if (response.isSuccess() && response.getData() != null) {
                var data = response.getData();
                balanceText = String.format("§aCarats: §f%.2f  §6Golden: §f%.2f",
                        data.carats, data.golden_carats);
            } else {
                balanceText = "§cNot registered";
            }
            isLoading = false;
        });

        // Load market
        api.getMarket().thenAccept(response -> {
            if (response.isSuccess() && response.getData() != null) {
                var data = response.getData();
                String changeColor = data.change_24h >= 0 ? "§a" : "§c";
                marketText = String.format("§7Carat: §f%.4f◆  %s%+.2f%%",
                        data.carat_price, changeColor, data.change_24h);
            } else {
                marketText = "§cMarket unavailable";
            }
        });
    }

    @Override
    public void render(DrawContext context, int mouseX, int mouseY, float delta) {
        this.renderBackground(context, mouseX, mouseY, delta);

        // Title
        context.drawCenteredTextWithShadow(this.textRenderer, this.title, this.width / 2, 20, 0xFFFFFF);

        // Balance and market info
        int infoY = 45;
        context.drawCenteredTextWithShadow(this.textRenderer, Text.literal(balanceText), this.width / 2, infoY, 0xFFFFFF);
        context.drawCenteredTextWithShadow(this.textRenderer, Text.literal(marketText), this.width / 2, infoY + 12, 0xFFFFFF);

        super.render(context, mouseX, mouseY, delta);
    }

    @Override
    public boolean shouldPause() {
        return false;
    }
}
