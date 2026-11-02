package forge.tnk;

import forge.ai.simulation.SimulationTest;
import forge.game.Game;
import forge.game.card.Card;
import forge.game.combat.Combat;
import forge.game.combat.CombatUtil;
import forge.game.phase.PhaseType;
import forge.game.player.Player;
import org.testng.annotations.Test;

import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertFalse;
import static org.testng.Assert.assertTrue;

/**
 * Direct-engine tests for TNK cards: place cards straight onto the battlefield and
 * inspect Card/Player state via TestNG asserts. This is the right style for static
 * abilities, P/T, and keywords -- things the declarative GameWrapper DSL (see
 * TnkTriggeredAbilityTest) has no assertion for.
 *
 * Requires TNK's custom cards installed into
 * ~/Library/Application Support/Forge/custom/cards/ -- run forge_export/install.sh
 * in the Tales MTG Set repo first. FModel.initialize() (called by AITest, the base
 * of SimulationTest) loads ForgeConstants.USER_CUSTOM_CARDS_DIR alongside the base
 * card database, so "Pakhar", "Derevenskiy Starosta", etc. resolve like any real card.
 */
public class TnkStaticAbilityTest extends SimulationTest {

    @Test
    public void derevenskiyStarosta_buffsOtherPeasants() {
        Game game = initAndCreateGame();
        Player p1 = game.getPlayers().get(0);
        game.getPhaseHandler().devModeSet(PhaseType.MAIN1, p1);

        addCard("Derevenskiy Starosta", p1);
        Card pakhar = addCard("Pakhar", p1); // printed 1/2 Human Peasant
        game.getAction().checkStateEffects(true);

        assertEquals(pakhar.getNetPower(), 1);
        assertEquals(pakhar.getNetToughness(), 3,
                "Pakhar should be 1/3 with Derevenskiy Starosta's +0/+1 static applied");
    }

    @Test
    public void derevenskiyStarosta_doesNotBuffItself() {
        Game game = initAndCreateGame();
        Player p1 = game.getPlayers().get(0);
        game.getPhaseHandler().devModeSet(PhaseType.MAIN1, p1);

        Card starosta = addCard("Derevenskiy Starosta", p1); // printed 2/3
        game.getAction().checkStateEffects(true);

        assertEquals(starosta.getNetToughness(), 3,
                "Starosta's own toughness should stay at its printed 2/3 -- the ability says \"Other\" Peasants");
    }

    @Test
    public void lisitsaKhitryuga_canOnlyBeBlockedByOneCreature() {
        Game game = initAndCreateGame();
        Player attackingPlayer = game.getPlayers().get(0);
        Player defendingPlayer = game.getPlayers().get(1);
        game.getPhaseHandler().devModeSet(PhaseType.COMBAT_DECLARE_BLOCKERS, attackingPlayer);

        Card fox = addCard("Lisitsa-Khitryuga", attackingPlayer);
        Card blocker1 = addCard("Grizzly Bears", defendingPlayer);
        Card blocker2 = addCard("Grizzly Bears", defendingPlayer);
        game.getAction().checkStateEffects(true);

        Combat combat = new Combat(attackingPlayer);
        combat.addAttacker(fox, defendingPlayer);
        game.getPhaseHandler().setCombat(combat);

        assertTrue(CombatUtil.canBlock(fox, blocker1, combat),
                "first blocker should still be a legal block");
        combat.addBlocker(fox, blocker1);

        assertFalse(CombatUtil.canBlock(fox, blocker2, combat),
                "Lisitsa-Khitryuga's Mode$ MinMaxBlocker (Max$ 1) should forbid a second blocker");
    }
}
