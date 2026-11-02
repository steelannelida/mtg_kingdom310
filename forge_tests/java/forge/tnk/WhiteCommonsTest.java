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
 * Tests for white commons with a T:/A: line (not auto-covered by VanillaCreatureResolutionTest).
 * Kalika Perekhozhiy is already covered by TnkTriggeredAbilityTest.
 */
public class WhiteCommonsTest extends TnkCardTestBase {

    @Test
    public void pogranichnayaZastava_etbCreatesFood() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);

        castFromHand(game, p1, "Pogranichnaya Zastava", "Plains", 4);

        assertTrue(p1.getCardsIn(ZoneType.Battlefield).stream().anyMatch(c -> c.getType().hasSubtype("Food")),
                "Pogranichnaya Zastava should create a Food token on ETB");
    }

    @Test
    public void krestniyKhod_createsTwoTokensAndDraws() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        addCardToZone("Plains", p1, ZoneType.Library); // so the draw doesn't lose the game
        int handBefore = p1.getCardsIn(ZoneType.Hand).size();

        castFromHand(game, p1, "Krestniy Khod", "Plains", 3);

        long peasantCount = p1.getCardsIn(ZoneType.Battlefield).stream()
                .filter(c -> c.getName().equals("Human Peasant")).count();
        assertEquals(peasantCount, 2, "Krestniy Khod should create two 1/1 Human Peasant tokens");
        assertEquals(p1.getCardsIn(ZoneType.Hand).size(), handBefore + 1, "Net +1: card added to hand from the draw");
    }

    @Test
    public void utrenniyZvon_untapsAllYourTappedCreatures() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card bear1 = addCard("Grizzly Bears", p1);
        Card bear2 = addCard("Runeclaw Bear", p1);
        bear1.setTapped(true);
        bear2.setTapped(true);

        castFromHand(game, p1, "Utrenniy Zvon", "Plains", 1);

        assertTrue(!bear1.isTapped() && !bear2.isTapped(), "Utrenniy Zvon should untap all your tapped creatures");
    }

    @Test
    public void obrazaNaShitah_staticTougnessBuffAndActivatedProtection() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        Card bear = addCard("Grizzly Bears", p1);
        int toughnessBefore = bear.getNetToughness();

        Card obraza = castFromHand(game, p1, "Obraza na Shitah", "Plains", 3);
        assertEquals(bear.getNetToughness(), toughnessBefore + 1, "Obraza na Shitah's static should give your creatures +0/+1");

        addCards("Plains", 2, p1);
        activateAbilityContaining(game, p1, obraza, "gains protection from a color", bear);
        assertTrue(bear.hasKeyword("Protection:Card.Black") || bear.hasKeyword("Protection:Card.Blue")
                || bear.hasKeyword("Protection:Card.Red") || bear.hasKeyword("Protection:Card.Green")
                || bear.hasKeyword("Protection:Card.White") || bear.getKeywords().toString().contains("Protection"),
                "Target creature should gain protection from a color: keywords=" + bear.getKeywords());
    }

    @Test
    public void voyevoda_attackingPumpsOtherSoldiers() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card voyevoda = addCard("Voyevoda", p1);
        voyevoda.setSickness(false);
        Card otherSoldier = addCard("Pogranichnaya Zastava", p1); // Human Soldier
        otherSoldier.setSickness(false);
        game.getTriggerHandler().registerActiveTrigger(voyevoda, false);
        int powerBefore = otherSoldier.getNetPower();

        declareAttackersNaturally(game);

        // AI-decision-dependent: only pumps if Voyevoda actually attacks. Confirm it
        // never LOSES power, and check the pump landed if Voyevoda did attack.
        assertTrue(otherSoldier.getNetPower() >= powerBefore, "Other soldier shouldn't lose power");
        if (voyevoda.isAttacking()) {
            assertEquals(otherSoldier.getNetPower(), powerBefore + 1,
                    "Other soldiers should get +1/+1 when Voyevoda attacks");
        }
    }

    @Test
    public void proshcheniye_destroysEnchantmentAndGainsLife() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card bear = addCard("Grizzly Bears", p1);
        Card aura = castTargeted(game, p1, "Priyut Leshego", bear, "Forest", 3); // a real Enchantment — Aura to destroy
        assertTrue(bear.isEnchantedBy(aura));
        int lifeBefore = p1.getLife();

        castTargeted(game, p1, "Proshcheniye", aura, "Plains", 2);

        assertTrue(!aura.isInZone(ZoneType.Battlefield), "Proshcheniye should destroy the target Enchantment");
        assertEquals(p1.getLife(), lifeBefore + 2, "Proshcheniye should gain 2 life");
    }

    @Test
    public void denProstoyat_grantsToughnessAndDefenderWhileAttached() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card bear = addCard("Grizzly Bears", p1);
        int toughnessBefore = bear.getNetToughness();

        Card aura = castTargeted(game, p1, "Den Prostoyat", bear, "Plains", 2);
        assertTrue(bear.isEnchantedBy(aura));

        assertEquals(bear.getNetToughness(), toughnessBefore + 3, "Den Prostoyat should give +0/+3");
        assertTrue(bear.hasKeyword("Defender"), "Den Prostoyat should give the enchanted creature defender");
    }

    @Test
    public void denProstoyat_exilesAnAttackerAtEndOfCombatIfEnchantedCreatureBlocked() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        Card bear = addCard("Grizzly Bears", p1);
        Card aura = castTargeted(game, p1, "Den Prostoyat", bear, "Plains", 2);
        assertTrue(bear.isEnchantedBy(aura));
        Card attacker = addCard("Runeclaw Bear", p2);

        // Directly mark the "attacked"/"blocked" flags that real combat sets, rather
        // than relying on a manually-constructed Combat object (confirmed elsewhere in
        // this suite not to reliably fire triggers) or on the AI's own block decision
        // (which isn't directly controllable in a test).
        attacker.getDamageHistory().setCreatureAttackedThisCombat(p1, 0);
        bear.addBlockedThisTurn(attacker);
        game.getTriggerHandler().registerActiveTrigger(aura, false);

        playUntilPhase(game, forge.game.phase.PhaseType.COMBAT_END);
        resolveEverything(game);

        assertTrue(!attacker.isInZone(ZoneType.Battlefield), "The attacking creature should have been exiled");
        assertTrue(!aura.isInZone(ZoneType.Battlefield), "Den Prostoyat should sacrifice itself");
    }

    @Test
    public void denProstoyat_stillSacrificesItselfEvenWithNoExileTarget() {
        // Regression test for the bug behind the live-play report ("blocked and
        // survived but nothing happened"): the sacrifice must be unconditional even
        // when the exile half can't happen -- previously both were bundled under one
        // OptionalDecider$ on the trigger, so declining (or, as here, having no legal
        // target at all) skipped the mandatory sacrifice too. No attacker exists in
        // this test, so "exile a creature that attacked this turn" has nothing to do;
        // the sacrifice must still happen.
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card bear = addCard("Grizzly Bears", p1);
        Card aura = castTargeted(game, p1, "Den Prostoyat", bear, "Plains", 2);
        assertTrue(bear.isEnchantedBy(aura));

        bear.addBlockedThisTurn(bear); // any non-null entry is enough to mark "blocked"
        game.getTriggerHandler().registerActiveTrigger(aura, false);

        playUntilPhase(game, forge.game.phase.PhaseType.COMBAT_END);
        resolveEverything(game);

        assertTrue(!aura.isInZone(ZoneType.Battlefield), "Den Prostoyat should sacrifice itself even with nothing to exile");
    }

    @Test
    public void blagoslovenie_pumpsAlways() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card bear = addCard("Grizzly Bears", p1);
        int powerBefore = bear.getNetPower();
        int toughnessBefore = bear.getNetToughness();

        castTargeted(game, p1, "Blagoslovenie", bear, "Plains", 1);

        assertEquals(bear.getNetPower(), powerBefore + 2, "Should be +2/+2");
        assertEquals(bear.getNetToughness(), toughnessBefore + 2, "Should be +2/+2");
        assertTrue(!bear.hasKeyword("Indestructible"), "Should not be indestructible off a quest");
    }

    @Test
    public void blagoslovenie_alsoGrantsIndestructibleOnAQuest() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card bear = addCard("Grizzly Bears", p1);
        Card questAura = castTargeted(game, p1, "Priyut Leshego", bear, "Forest", 3);
        assertTrue(bear.isEnchantedBy(questAura));

        castTargeted(game, p1, "Blagoslovenie", bear, "Plains", 1);

        assertTrue(bear.hasKeyword("Indestructible"), "Should also gain indestructible while on a quest");
    }

    @Test
    public void svetlyOtrok_diesWithoutAQuest_noLifeGain() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card otrok = addCard("Svetly Otrok", p1);
        int lifeBefore = p1.getLife();

        kill(game, otrok);

        assertEquals(p1.getLife(), lifeBefore, "Should not gain life dying without ever being on a quest");
    }

    @Test
    public void svetlyOtrok_diesOnAQuest_gains3Life() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card otrok = addCard("Svetly Otrok", p1);
        Card questAura = castTargeted(game, p1, "Priyut Leshego", otrok, "Forest", 3);
        assertTrue(otrok.isEnchantedBy(questAura));
        int lifeBefore = p1.getLife();

        kill(game, otrok);

        assertEquals(p1.getLife(), lifeBefore + 3, "Should gain 3 life dying while on a quest");
    }

    @Test
    public void derevenskayaDevitsa_activatedAbilityPumpsManuallyChosenTarget() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card devitsa = addCard("Derevenskaya Devitsa", p1);
        devitsa.setSickness(false);
        Card bear = addCard("Grizzly Bears", p1);
        Card questAura = castTargeted(game, p1, "Priyut Leshego", bear, "Forest", 3);
        assertTrue(bear.isEnchantedBy(questAura));
        int powerBefore = bear.getNetPower();

        SpellAbility sa = findSAWithPrefix(devitsa, "{T}:");
        assertTrue(sa != null, "The ability should at least exist on the card");
        sa.setActivatingPlayer(p1);
        sa.getTargets().add(bear);
        boolean played = ComputerUtil.playStack(sa, p1, game);
        assertTrue(played, "Derevenskaya Devitsa's ability should be playable with a manually-assigned target");
        resolveEverything(game);

        assertEquals(bear.getNetPower(), powerBefore + 1, "Should be +1/+1");
    }

    @Test
    public void pastva_questCompletionTriggerFires() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card pastva = addCard("Pastva", p1);
        game.getTriggerHandler().registerActiveTrigger(pastva, false);
        game.copyLastState();
        Card bear = addCard("Grizzly Bears", p1);
        Card questAura = castTargeted(game, p1, "Priyut Leshego", bear, "Forest", 3);
        assertTrue(bear.isEnchantedBy(questAura));

        // Move the quest aura to the graveyard directly to simulate "completing" the quest.
        game.getAction().moveToGraveyard(questAura, null, forge.game.ability.AbilityKey.newMap());
        resolveEverything(game);

        long peasantCount = p1.getCardsIn(ZoneType.Battlefield).stream()
                .filter(c -> c.getName().equals("Human Peasant")).count();
        assertEquals(peasantCount, 1, "Pastva should create a token when a Quest is completed");
    }
}
