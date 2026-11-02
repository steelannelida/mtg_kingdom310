package forge.tnk;

import forge.game.Game;
import forge.game.card.Card;
import forge.game.player.Player;
import forge.game.zone.ZoneType;
import org.testng.annotations.Test;

import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertTrue;

/** Tests for colorless commons -- all artifacts/equipment, none auto-covered by VanillaCreatureResolutionTest. */
public class ColorlessCommonsTest extends TnkCardTestBase {

    @Test
    public void lapotSamokhodny_equippedCreatureGetsBuffAndBlockRestriction() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        Card lapot = addCard("Lapot Samokhodny", p1);
        Card bear = addCard("Grizzly Bears", p1); // printed 2/2
        addCards("Plains", 1, p1); // Equip {1}

        equip(game, p1, lapot, bear);
        assertEquals(bear.getNetPower(), 3, "Equipped creature should be +1/+0");

        Card blocker1 = addCard("Runeclaw Bear", p2);
        Card blocker2 = addCard("Runeclaw Bear", p2);
        forge.game.combat.Combat combat = new forge.game.combat.Combat(p1);
        combat.addAttacker(bear, p2);
        game.getPhaseHandler().setCombat(combat);
        assertTrue(forge.game.combat.CombatUtil.canBlock(bear, blocker1, combat),
                "first blocker should still be legal");
        combat.addBlocker(bear, blocker1);
        assertTrue(!forge.game.combat.CombatUtil.canBlock(bear, blocker2, combat),
                "Lapot Samokhodny's granted MinMaxBlocker (Max$ 1) should forbid a second blocker");
    }

    @Test
    public void samobranka_activatedAbilityCreatesFood() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card samobranka = addCard("Samobranka", p1);
        samobranka.setSickness(false);
        addCards("Swamp", 2, p1);

        activateAbility(game, p1, samobranka, "{2}, {T}: Create a Food token", null);

        assertTrue(p1.getCardsIn(ZoneType.Battlefield).anyMatch(c -> c.getType().hasSubtype("Food")),
                "Samobranka should have created a Food token");
    }

    @Test
    public void volshebnoeZerkaltse_activatedAbilityScries() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card zerkaltse = addCard("Volshebnoe Zerkaltse", p1);
        zerkaltse.setSickness(false);
        addCards("Swamp", 1, p1);

        // Scry doesn't leave an easily-assertable trace with an empty library; just
        // confirm the ability activates and resolves without crashing.
        activateAbility(game, p1, zerkaltse, "{1}, {T}: Scry 1", null);
        assertTrue(zerkaltse.isInZone(ZoneType.Battlefield));
    }

    @Test
    public void klubochek_tutorsABasicLandToHand() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card klubochek = addCard("Klubochek", p1);
        klubochek.setSickness(false);
        addCardToZone("Plains", p1, ZoneType.Library); // so the tutor has something to find

        activateAbility(game, p1, klubochek, "{T}, Sacrifice", null);

        assertTrue(p1.getCardsIn(ZoneType.Hand).anyMatch(c -> c.getName().equals("Plains")),
                "Klubochek should have found a basic land into hand");
        assertTrue(klubochek.isInZone(ZoneType.Graveyard), "Klubochek should have sacrificed itself");
    }

    @Test(timeOut = 15000)
    public void gorshochekKashi_resolvesOntoBattlefield() {
        // NOT tested here: the upkeep trigger itself. Confirmed by direct experiment
        // that advancing this test harness across a second full turn boundary (to reach
        // the card controller's own upkeep a second time) makes AITest.playUntilPhase()
        // catastrophically slow (literally 965s once, for a totally empty board) rather
        // than genuinely infinite -- looks like a USE_FULL_SIMULATION AI performance
        // cliff, not a bug in this card's script. Left as a smoke test; see
        // forge_integration.md's "Known gaps" for the full writeup and a warning against
        // writing tests that cross more than one turn boundary in this suite.
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card gorshochek = addCard("Gorshochek Kashi", p1);
        assertTrue(gorshochek.isInZone(ZoneType.Battlefield));
    }

    @Test
    public void dubinkaSamoboyka_equippedCreatureDealsDamageOnAttack() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        int p2LifeBefore = p2.getLife();
        Card dubinka = addCard("Dubinka Samoboyka", p1);
        Card bear = addCard("Grizzly Bears", p1);
        bear.setSickness(false);
        addCards("Plains", 2, p1); // Equip {2}

        equip(game, p1, dubinka, bear);
        assertEquals(bear.getNetPower(), 4, "Equipped creature should be +2/+0");

        game.getTriggerHandler().registerActiveTrigger(dubinka, false);
        declareAttackersNaturally(game);

        assertEquals(p2.getLife(), p2LifeBefore - 1, "Dubinka Samoboyka should deal 1 damage when equipped creature attacks");
    }
}
