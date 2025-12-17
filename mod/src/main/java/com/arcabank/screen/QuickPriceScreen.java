package com.arcabank.screen;

import com.arcabank.ArcaBankClient;
import com.arcabank.api.ArcaApiClient;
import net.minecraft.client.gui.DrawContext;
import net.minecraft.client.gui.screen.Screen;
import net.minecraft.client.gui.widget.ButtonWidget;
import net.minecraft.client.gui.widget.TextFieldWidget;
import net.minecraft.text.Text;

/**
 * Quick price check screen
 */
public class QuickPriceScreen extends Screen {
    private static final int FIELD_WIDTH = 200;

    private final Screen parent;
    private TextFieldWidget itemNameField;
    private String resultText = "";
    private boolean isSearching = false;

    public QuickPriceScreen(Screen parent) {
        super(Text.translatable("arcabank.screen.price_check"));
        this.parent = parent;
    }

    @Override
    protected void init() {
        super.init();

        int centerX = this.width / 2;
        int startY = this.height / 2 - 40;

        // Item name input field
        itemNameField = new TextFieldWidget(
                this.textRenderer,
                centerX - FIELD_WIDTH / 2,
                startY,
                FIELD_WIDTH,
                20,
                Text.translatable("arcabank.label.item_name")
        );
        itemNameField.setPlaceholder(Text.literal("Enter item name..."));
        itemNameField.setMaxLength(100);
        this.addSelectableChild(itemNameField);
        this.setInitialFocus(itemNameField);

        // Search button
        this.addDrawableChild(ButtonWidget.builder(
                Text.translatable("arcabank.button.check_price"),
                button -> searchPrice()
        ).dimensions(centerX - 100, startY + 30, 95, 20).build());

        // Back button
        this.addDrawableChild(ButtonWidget.builder(
                Text.translatable("arcabank.button.back"),
                button -> this.close()
        ).dimensions(centerX + 5, startY + 30, 95, 20).build());
    }

    private void searchPrice() {
        String itemName = itemNameField.getText().trim();
        if (itemName.isEmpty()) {
            resultText = "§cPlease enter an item name";
            return;
        }

        isSearching = true;
        resultText = "§7Searching...";

        ArcaBankClient.getApiClient().getItemPrice(itemName).thenAccept(response -> {
            isSearching = false;
            if (response.isSuccess() && response.getData() != null) {
                var data = response.getData();
                if (data.found) {
                    resultText = String.format(
                            "§a%s\n§7Category: §f%s\n§7Price: §f%.4f carats\n§724h Volume: §f%.2f carats\n§7Trades: §f%d",
                            data.item_name,
                            data.category,
                            data.current_price,
                            data.volume_24h,
                            data.trade_count_24h
                    );
                } else {
                    resultText = "§eNo price data found for: " + itemName;
                }
            } else {
                resultText = "§c" + (response.getError() != null ? response.getError() : "Failed to get price");
            }
        });
    }

    @Override
    public void render(DrawContext context, int mouseX, int mouseY, float delta) {
        this.renderBackground(context, mouseX, mouseY, delta);

        // Title
        context.drawCenteredTextWithShadow(this.textRenderer, this.title, this.width / 2, 20, 0xFFFFFF);

        // Label
        context.drawTextWithShadow(this.textRenderer,
                Text.translatable("arcabank.label.item_name"),
                this.width / 2 - FIELD_WIDTH / 2,
                this.height / 2 - 52,
                0xAAAAAA);

        // Render text field
        itemNameField.render(context, mouseX, mouseY, delta);

        // Result text (multiline)
        if (!resultText.isEmpty()) {
            String[] lines = resultText.split("\n");
            int y = this.height / 2 + 20;
            for (String line : lines) {
                context.drawCenteredTextWithShadow(this.textRenderer, Text.literal(line), this.width / 2, y, 0xFFFFFF);
                y += 12;
            }
        }

        super.render(context, mouseX, mouseY, delta);
    }

    @Override
    public boolean keyPressed(int keyCode, int scanCode, int modifiers) {
        if (keyCode == 257 && itemNameField.isFocused()) { // Enter key
            searchPrice();
            return true;
        }
        return super.keyPressed(keyCode, scanCode, modifiers);
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
