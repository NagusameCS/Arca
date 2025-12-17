package com.arcabank;

import com.arcabank.api.ArcaApiClient;
import com.arcabank.keybind.KeyBindings;
import com.arcabank.config.ArcaConfig;
import net.fabricmc.api.ClientModInitializer;
import net.fabricmc.fabric.api.client.event.lifecycle.v1.ClientTickEvents;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * Arca Bank Fabric Mod - Client Entry Point
 * Provides in-game integration with the Arca Bank economy system.
 */
public class ArcaBankClient implements ClientModInitializer {
    public static final String MOD_ID = "arcabank";
    public static final Logger LOGGER = LoggerFactory.getLogger(MOD_ID);

    private static ArcaApiClient apiClient;
    private static ArcaConfig config;

    @Override
    public void onInitializeClient() {
        LOGGER.info("Initializing Arca Bank client mod...");

        // Load configuration
        config = ArcaConfig.load();

        // Initialize API client
        apiClient = new ArcaApiClient(config.getApiUrl());

        // Register keybindings
        KeyBindings.register();

        // Register tick event for keybind handling
        ClientTickEvents.END_CLIENT_TICK.register(KeyBindings::onEndTick);

        LOGGER.info("Arca Bank client mod initialized! API: {}", config.getApiUrl());
    }

    public static ArcaApiClient getApiClient() {
        return apiClient;
    }

    public static ArcaConfig getConfig() {
        return config;
    }

    public static void reloadConfig() {
        config = ArcaConfig.load();
        apiClient = new ArcaApiClient(config.getApiUrl());
        LOGGER.info("Configuration reloaded. API: {}", config.getApiUrl());
    }
}
