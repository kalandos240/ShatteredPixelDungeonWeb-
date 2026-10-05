/*
 * Pixel Dungeon
 * Copyright (C) 2012-2015 Oleg Dolya
 *
 * Shattered Pixel Dungeon
 * Copyright (C) 2014-2026 Evan Debenham
 *
 * Web port modifications, 2026.
 *
 * This program is free software: you can redistribute it and/or modify
 * it under the terms of the GNU General Public License as published by
 * the Free Software Foundation, either version 3 of the License, or
 * (at your option) any later version.
 */

package com.shatteredpixel.shatteredpixeldungeon.web;

import com.badlogic.gdx.Gdx;
import com.badlogic.gdx.graphics.Pixmap;
import com.badlogic.gdx.graphics.g2d.PixmapPacker;
import com.badlogic.gdx.graphics.g2d.freetype.FreeTypeFontGenerator;
import com.watabou.utils.PlatformSupport;

import java.util.ArrayList;
import java.util.HashMap;

public class WebPlatformSupport extends PlatformSupport {

    private static FreeTypeFontGenerator basicFontGenerator;
    private static FreeTypeFontGenerator asianFontGenerator;

    @Override
    public void updateDisplaySize() {
        // The browser canvas tracks the host viewport.
    }

    @Override
    public boolean supportsFullScreen() {
        // Browser fullscreen requires a user gesture. Keep the game's fullscreen
        // toggle disabled until a dedicated web UI flow is added.
        return false;
    }

    @Override
    public void updateSystemUI() {
        // No native system bars to control in the browser.
    }

    @Override
    public boolean connectedToUnmeteredNetwork() {
        return true;
    }

    @Override
    public boolean supportsVibration() {
        return false;
    }

    @Override
    public void setupFontGenerators(int pageSize, boolean systemFont) {
        if (fonts != null && this.pageSize == pageSize && this.systemfont == systemFont) {
            return;
        }

        this.pageSize = pageSize;
        this.systemfont = systemFont;

        resetGenerators(false);
        fonts = new HashMap<>();

        if (systemFont) {
            basicFontGenerator = asianFontGenerator =
                    new FreeTypeFontGenerator(Gdx.files.internal("fonts/droid_sans.ttf"));
        } else {
            basicFontGenerator =
                    new FreeTypeFontGenerator(Gdx.files.internal("fonts/pixel_font.ttf"));
            asianFontGenerator =
                    new FreeTypeFontGenerator(Gdx.files.internal("fonts/droid_sans.ttf"));
        }

        fonts.put(basicFontGenerator, new HashMap<>());
        fonts.put(asianFontGenerator, new HashMap<>());

        packer = new PixmapPacker(pageSize, pageSize, Pixmap.Format.RGBA8888, 1, false);
    }

    @Override
    protected FreeTypeFontGenerator getGeneratorForString(String input) {
        for (int i = 0; i < input.length(); i++) {
            if (usesAsianFont(input.charAt(i))) {
                return asianFontGenerator;
            }
        }
        return basicFontGenerator;
    }

    private static boolean usesAsianFont(char c) {
        return isHangul(c)
                || isCjkIdeograph(c)
                || isCjkSymbol(c)
                || isHiragana(c)
                || isKatakana(c)
                || (c >= '\uFF00' && c <= '\uFFEF'); // half/full-width forms
    }

    private static boolean isHangul(char c) {
        return c >= '\uAC00' && c <= '\uD7AF';
    }

    private static boolean isCjkIdeograph(char c) {
        return c >= '\u4E00' && c <= '\u9FFF';
    }

    private static boolean isCjkSymbol(char c) {
        return c >= '\u3000' && c <= '\u303F';
    }

    private static boolean isHiragana(char c) {
        return c >= '\u3040' && c <= '\u309F';
    }

    private static boolean isKatakana(char c) {
        return c >= '\u30A0' && c <= '\u30FF';
    }

    private static boolean isSplitCharacter(char c, boolean multiline) {
        return c == '\n'
                || c == '_'
                || (multiline && c == ' ')
                || isHiragana(c)
                || isKatakana(c)
                || isCjkIdeograph(c)
                || isCjkSymbol(c);
    }

    /**
     * Mirrors the desktop regex splitter without depending on Unicode-block
     * regular expressions, which TeaVM 0.15.0's regex implementation rejects.
     * Newlines, underscores, optional spaces, CJK/Japanese characters and the
     * markdown "**" marker remain isolated tokens.
     */
    @Override
    public String[] splitforTextBlock(String text, boolean multiline) {
        ArrayList<String> result = new ArrayList<>();
        StringBuilder normal = new StringBuilder();

        int i = 0;
        while (i < text.length()) {
            char c = text.charAt(i);

            if (c == '*' && i + 1 < text.length() && text.charAt(i + 1) == '*') {
                flush(normal, result);
                result.add("**");
                i += 2;
                continue;
            }

            if (isSplitCharacter(c, multiline)) {
                flush(normal, result);
                result.add(String.valueOf(c));
                i++;
                continue;
            }

            normal.append(c);
            i++;
        }

        flush(normal, result);
        return result.toArray(new String[0]);
    }

    private static void flush(StringBuilder normal, ArrayList<String> result) {
        if (normal.length() > 0) {
            result.add(normal.toString());
            normal.setLength(0);
        }
    }
}
