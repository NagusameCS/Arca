package com.arcabank.screen;

import com.arcabank.ArcaBankClient;
import net.minecraft.client.MinecraftClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.text.Text;

/**
 * Screen showing player's trading statistics
 */
public class MyStatsScreen extends Screen {
    private final Screen parent;
    private String[] statsLines = {"§7Loading..."};
    private boolean isLoading = true;

    public MyStatsScreen(Screen parent) {
        super(Text.translatable("arcabank.screen.my_stats"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        super.init();

        // Back button
        this.addDrawableChild(ButtonWidget.builder(
                Text.translatable("arcabank.button.back"),
                button -> this.close()
        ).dimensions(this.width / 2 - 50, this.height - 40, 100, 20).build());

        loadStats();
    }

    private void loadStats() {
        MinecraftClient client = MinecraftClient.getInstance();
        if (client.player == null) {
            statsLines = new String[]{"§cNo player found"};
            isLoading = false;
            return;
        }

        String uuid = client.player.getUuidAsString();

        ArcaBankClient.getApiClient().getTradeStats(uuid).thenAccept(response -> {
            isLoading = false;
            if (response.isSuccess() && response.getData() != null) {
                var data = response.getData();

                if (!data.has_stats) {
                    statsLines = new String[]{
                            "§eNo trading history yet",
                            "",
                            "§7Report your first trade to start",
                            "§7building your trading reputation!"
                    };
                } else {
                    statsLines = new String[]{
                            "§6═══ Trading Statistics ═══",
                            "",
                            String.format("§7Total Trades: §f%d", data.total_trades),
                            String.format("§7Buys: §a%d §7| Sells: §c%d", data.buy_count, data.sell_count),
                            "",
                            String.format("§7Total Volume: §f%.2f §7carats", data.total_volume),
                            String.format("§7Average Trade: §f%.2f §7carats", data.average_trade_size),
                            "",
                            String.format("§7Verified Trades: §a%d", data.verified_trades),
                            String.format("§7Reputation: %s%.1f%%",
                                    data.reputation >= 80 ? "§a" : data.reputation >= 50 ? "§e" : "§c",
                                    data.reputation),
                    };
                }
            } else {
                statsLines = new String[]{
                        "§c" + (response.getError() != null ? response.getError() : "Failed to load stats")
                };
            }
        });
    }

    @Override
    public void render(DrawContext context, int mouseX, int mouseY, float delta) {
        this.renderBackground(context, mouseX, mouseY, delta);

        // Title
        context.drawCenteredTextWithShadow(this.textRenderer, this.title, this.width / 2, 20, 0xFFFFFF);

        // Stats
        int y = 50;
        for (String line : statsLines) {
            context.drawCenteredTextWithShadow(this.textRenderer, Text.literal(line), this.width / 2, y, 0xFFFFFF);
            y += 14;
        }

        super.render(context, mouseX, mouseY, delta);
    }

    @Override
    public void close() {
        if (parent != null) {
            this.client.setScreen(parent);
        } else {
            super.close();
        }
    }

    @Override
    public boolean shouldPause() {
        return false;
    }
}
