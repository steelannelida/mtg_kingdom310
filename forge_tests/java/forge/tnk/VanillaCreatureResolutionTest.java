package forge.tnk;

import java.util.ArrayList;
import java.util.List;

import forge.game.Game;
import forge.game.card.Card;
import forge.game.player.Player;
import forge.game.zone.ZoneType;
import org.testng.annotations.DataProvider;
import org.testng.annotations.Test;

import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertNotNull;
import static org.testng.Assert.assertTrue;

/**
 * Data-driven smoke test: for every TNK creature whose forge: block has neither a
 * triggered (T:) nor an activated (A:) ability -- i.e. nothing whose SVar-referenced
 * body is only parsed lazily on fire/activation -- casting and resolving it exercises
 * the *entire* forge: block (Name/ManaCost/Types/PT/K:/S: all get built into real
 * objects the moment the card is constructed, cast or not; casting on top of that also
 * exercises the mana cost and the zone-change resolution path).
 *
 * Doesn't cover: auras/enchantments needing a target, anything with a T: or A: line
 * (see TnkTriggeredAbilityTest / TnkStaticAbilityTest for those), or mana costs with
 * hybrid/Phyrexian/X/snow symbols (ManaCostUtil.landsFor returns null for those and
 * the card is silently excluded from the data provider -- not silently skipped as a
 * false pass, just not offered as a row).
 */
public class VanillaCreatureResolutionTest extends TnkCardTestBase {

    @Test
    public void catalogActuallyLoaded() {
        // Guards against a wrong tnk.exportDir silently producing zero data-provider
        // rows, which TestNG would otherwise report as "0 tests, all green".
        assertTrue(TnkCardCatalog.loadAll().size() > 0,
                "TnkCardCatalog found no cards -- check the tnk.exportDir path");
    }

    @DataProvider(name = "vanillaCreatures")
    public Object[][] vanillaCreatures() {
        List<Object[]> rows = new ArrayList<>();
        for (TnkCardCatalog.ExportedCard c : TnkCardCatalog.loadAll()) {
            if (!c.isCreature() || !c.hasNoAbilities() || c.power == null) {
                continue;
            }
            List<String> lands = ManaCostUtil.landsFor(c.manaCost);
            if (lands == null) {
                continue; // unsupported mana cost shape (hybrid/X/snow/...)
            }
            rows.add(new Object[]{c.name, lands, c.power, c.toughness});
        }
        return rows.toArray(new Object[0][]);
    }

    @Test(dataProvider = "vanillaCreatures")
    public void resolvesWithPrintedStats(String cardName, List<String> lands,
            int expectedPower, int expectedToughness) {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);

        Card resolved = castFromHand(game, p1, cardName, lands);

        assertNotNull(resolved, cardName + " should have resolved");
        assertTrue(resolved.isInZone(ZoneType.Battlefield), cardName + " should be on the battlefield");
        assertEquals(resolved.getNetPower(), expectedPower, cardName + " power mismatch");
        assertEquals(resolved.getNetToughness(), expectedToughness, cardName + " toughness mismatch");
    }
}
