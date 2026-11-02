package forge.tnk;

import forge.ai.ComputerUtil;
import forge.game.Game;
import forge.game.card.Card;
import forge.game.player.Player;
import forge.game.spellability.SpellAbility;
import forge.game.zone.ZoneType;
import org.testng.annotations.Test;

import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertTrue;

/**
 * Verifies the single pattern the whole Quest mechanic's cross-card checks rely on:
 * "Creature.EnchantedBy Aura.Quest" correctly identifies a creature enchanted by a
 * Quest-subtype Aura, from a DIFFERENT card's perspective. ~12 cards across colors use
 * this exact filter (Okhrabrevshiy Mujik, Derevenskaya Devitsa, Voron-Vestnik,
 * Bogatyrskaya Sila, Konny Druzhinnnik, Svetly Otrok, ... ), so this one test protects
 * a lot of coverage at once.
 *
 * "Quest" needed two fixes to work as a real Aura subtype, both confirmed via
 * engine-level debug instrumentation (forge-src is a scratch clone; instrumentation
 * added and reverted with `git checkout --` once understood, same as the earlier
 * dies-trigger investigation): (1) "Quest" wasn't a supertype/subtype Forge's CardType
 * recognized at all, so it was silently stripped at load time -- fixed by adding
 * `Quest:Quests` to the `[EnchantmentTypes]` section of Forge's own
 * `res/lists/TypeLists.txt` (a plain data file, not a compiled enum -- this needs to be
 * patched in every real Forge install this set is played in, not just the dev/test
 * clone). (2) Even with the type correctly preserved, every card script used a
 * lowercase `Aura.quest` -- `CardType.hasStringType()` capitalizes its input before
 * checking against Supertype/CoreType enums, but checks the raw (uncapitalized) subtype
 * set FIRST, so a lowercase query never matches the capitalized "Quest" subtype string
 * actually stored on the card. Fixed by capitalizing every `Aura.quest` reference to
 * `Aura.Quest` across `cards/common/*.yaml`.
 */
public class QuestStateCheckTest extends TnkCardTestBase {

    /** Casts an Aura and manually attaches it (castFromHand() doesn't handle targeting). */
    private Card castAura(Game game, Player p, String auraName, Card enchant, String basicLand, int landCount) {
        for (int i = 0; i < landCount; i++) {
            addCard(basicLand, p);
        }
        Card card = addCardToZone(auraName, p, ZoneType.Hand);
        SpellAbility sa = card.getSpells().get(0);
        sa.setActivatingPlayer(p);
        sa.getTargets().add(enchant);
        boolean played = ComputerUtil.playStack(sa, p, game);
        assertTrue(played, auraName + " should have been castable targeting " + enchant.getName());
        game.getStack().resolveStack();
        resolveEverything(game);
        return findCardWithName(game, auraName);
    }

    @Test
    public void konnyDruzhinnnik_getsFirstStrikeOnceOnAQuest() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);

        Card konny = addCard("Konny Druzhinnnik", p1);
        assertTrue(!konny.hasKeyword("First Strike"), "Should not have first strike before questing");

        Card aura = castAura(game, p1, "Priyut Leshego", konny, "Forest", 3);
        assertTrue(konny.isEnchantedBy(aura), "Priyut Leshego should be attached to Konny Druzhinnnik");
        assertEquals(konny.getNetToughness(), 3, "Priyut Leshego's own +1/+1 static should apply too");

        assertTrue(konny.hasKeyword("First Strike"), "Konny Druzhinnnik should gain first strike once on a quest");
    }

    @Test
    public void okhrabrevshiyMujik_getsPowerBoostOnceOnAQuest() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);

        Card mujik = addCard("Okhrabrevshiy Mujik", p1); // printed 2/2
        assertEquals(mujik.getNetPower(), 2, "Should be base 2 power before questing");

        castAura(game, p1, "Priyut Leshego", mujik, "Forest", 3);

        // 2 base + 1 from Priyut Leshego's own unconditional "enchanted creature gets
        // +1/+1" + 1 from mujik's own "+1/+0 as long as it's on a quest" conditional
        // static = 4. (An earlier version of this test asserted 3 -- that was a false
        // positive that only measured the Aura's own bonus, from before mujik's own
        // conditional static was confirmed broken and then fixed; see the class doc.)
        assertEquals(mujik.getNetPower(), 4, "Okhrabrevshiy Mujik should be +1/+0 once on a quest, on top of Priyut Leshego's own +1/+1");
    }
}
