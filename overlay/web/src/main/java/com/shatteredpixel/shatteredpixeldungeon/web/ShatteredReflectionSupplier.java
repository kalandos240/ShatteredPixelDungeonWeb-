/*
 * Shattered Pixel Dungeon web port modifications, 2026.
 *
 * This file is distributed under the GNU General Public License v3 or later.
 */

package com.shatteredpixel.shatteredpixeldungeon.web;

import org.teavm.classlib.ReflectionContext;
import org.teavm.classlib.ReflectionSupplier;
import org.teavm.model.ClassReader;
import org.teavm.model.MethodDescriptor;

import java.util.Collection;
import java.util.Collections;

/**
 * Shattered stores concrete Bundlable class names and later restores them via
 * Class.forName + a no-argument constructor. The stock gdx-teavm reflection
 * registration exposes every field/method of every matched class, which is far
 * more metadata than Shattered needs and makes TeaVM's dependency graph huge.
 *
 * This supplier deliberately exposes only:
 *  - lookup by runtime class name for Shattered/Watabou classes;
 *  - the zero-argument constructor when a class has one.
 *
 * Game serialization itself is explicit storeInBundle/restoreFromBundle code,
 * so fields and ordinary methods do not need reflective access.
 */
@SuppressWarnings("deprecation")
public final class ShatteredReflectionSupplier implements ReflectionSupplier {

    private static final MethodDescriptor NO_ARG_CONSTRUCTOR =
            new MethodDescriptor("<init>", void.class);

    private static boolean isGameClass(String className) {
        return className.startsWith("com.shatteredpixel.shatteredpixeldungeon.")
                || className.startsWith("com.watabou.");
    }

    @Override
    public boolean isClassFoundByName(ReflectionContext context, String className) {
        return isGameClass(className);
    }

    @Override
    public Collection<MethodDescriptor> getAccessibleMethods(
            ReflectionContext context, String className) {

        if (!isGameClass(className)) {
            return Collections.emptyList();
        }

        ClassReader cls = context.getClassSource().get(className);
        if (cls == null || cls.getMethod(NO_ARG_CONSTRUCTOR) == null) {
            return Collections.emptyList();
        }

        return Collections.singleton(NO_ARG_CONSTRUCTOR);
    }
}
