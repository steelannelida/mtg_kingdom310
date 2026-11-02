package forge.tnk;

import forge.ai.ComputerUtil;
import forge.game.Game;
import forge.game.card.Card;
import forge.game.phase.PhaseType;
import forge.game.player.Player;
import forge.game.spellability.SpellAbility;
import forge.game.zone.ZoneType;
import org.testng.annotations.Test;

import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertNotNull;
import static org.testng.Assert.assertTrue;

/**
 * Tests for black commons using patterns not covered by BlackCommonsTest: Morbid,
 * optional-sacrifice-cost triggers, conditional-on-graveyard-card-type effects, Nakaz
 * (Flash enchantment with a curse), and a Quest aura. These are the harder scripts in
 * this batch -- see forge_integration.md's "Known gaps" section for ones left
 * deliberately imperfect.
 */
public class BlackCommonsAdvancedTest extends TnkCardTestBase {

    @Test
    public void mertvetsIzNavi_morbidEtbReturnsCreatureFromGraveyard() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        // Morbid needs a creature to have died THIS turn -- kill a throwaway one first.
        // kill()'s resolveEverything() can drive the game past MAIN1 (even into a new
        // turn) chasing an empty stack with nothing else going on; reset the phase back
        // so "died this turn" still refers to the turn the kill happened in.
        Card victim = addCard("Grizzly Bears", p1); // cmc 2
        kill(game, victim);
        game.getPhaseHandler().devModeSet(PhaseType.MAIN1, p1);

        castFromHand(game, p1, "Mertvets iz Navi", "Swamp", 4);

        assertTrue(p1.getCardsIn(ZoneType.Hand).contains(victim),
                "Morbid should have returned the cmc-2 creature to hand");
    }

    @Test
    public void chertMelkiy_etbResolvesWithOptionalSacrificeAvailable() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        addCard("Grizzly Bears", p1); // fodder the AI may choose to sacrifice

        castFromHand(game, p1, "Chert Melkiy", "Swamp", 2);

        // Paying the optional sac cost is an AI choice, not ours to force -- just confirm
        // the ETB with an optional-cost ability resolves without crashing.
        assertTrue(findCardWithName(game, "Chert Melkiy") != null, "Chert Melkiy should resolve");
    }

    @Test
    public void kladbishchenskiyVor_etbTreasureIfExiledCardWasCreature() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        Card inGrave = addCardToZone("Grizzly Bears", p2, ZoneType.Graveyard);

        castFromHand(game, p1, "Kladbishchenskiy vor", "Swamp", 3);

        assertTrue(inGrave.isInZone(ZoneType.Exile), "Targeted graveyard card should be exiled");
        assertTrue(p1.getCardsIn(ZoneType.Battlefield).anyMatch(c -> c.getType().hasSubtype("Treasure")),
                "Exiling a creature card should have created a Treasure token");
    }

    @Test
    public void trupOzhivshiy_costsLessWithMorbid() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card victim = addCard("Grizzly Bears", p1);
        kill(game, victim);

        // Full cost is {4}{B} (5 mana); Morbid should make it payable with 3.
        Card trup = castFromHand(game, p1, "Trup Ozhivshiy", "Swamp", 3);

        assertTrue(trup.isInZone(ZoneType.Battlefield), "Trup Ozhivshiy should be castable for 3 with Morbid active");
    }

    @Test
    public void neOglyadyvaisya_etbReanimatesThenSacrificesOnNextGraveyardEntry() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card inGrave = addCardToZone("Grizzly Bears", p1, ZoneType.Graveyard);

        Card nakaz = castFromHand(game, p1, "Ne Oglyadyvaisya", "Swamp", 2);
        assertTrue(inGrave.isInZone(ZoneType.Battlefield), "Ne Oglyadyvaisya should reanimate the targeted creature");

        // Now put another card into p1's graveyard -- the curse should sacrifice itself + a creature.
        kill(game, inGrave);

        assertTrue(nakaz.isInZone(ZoneType.Graveyard),
                "Ne Oglyadyvaisya should sacrifice itself once a card enters its controller's graveyard");
    }

    @Test
    public void nochProderzhatsa_survivingABlockDrawsAndSacrifices() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        Card blocker = addCard("Wall of Omens", p1); // printed 0/4, -1/-1 from the aura -> 0/3
        Card attacker = addCard("Grizzly Bears", p2); // 2/2
        for (int i = 0; i < 2; i++) {
            addCardToZone("Swamp", p1, ZoneType.Library); // so the draw has something to draw
        }

        Card aura = castTargeted(game, p1, "Noch Proderzhatsa", blocker, "Swamp", 2);
        assertTrue(blocker.isEnchantedBy(aura), "Aura should be attached to the blocker");
        int handBefore = p1.getCardsIn(ZoneType.Hand).size();

        // Fire the real "Blocks" trigger event directly (with the same runParams shape
        // PhaseHandler uses when a block is actually declared: AbilityKey.Blocker +
        // AbilityKey.Attackers) rather than relying on natural combat -- the AI's own
        // block decision isn't reliably controllable in a test, and a
        // manually-constructed Combat object doesn't carry blocks through to the real
        // combat-damage step (confirmed elsewhere in this suite). This is what
        // registers Noch Proderzhatsa's delayed "check at end of combat" trigger.
        game.getTriggerHandler().registerActiveTrigger(aura, false);
        java.util.Map<forge.game.ability.AbilityKey, Object> runParams = forge.game.ability.AbilityKey.newMap();
        runParams.put(forge.game.ability.AbilityKey.Blocker, blocker);
        runParams.put(forge.game.ability.AbilityKey.Attackers, java.util.List.of(attacker));
        game.getTriggerHandler().runTrigger(forge.game.trigger.TriggerType.Blocks, runParams, false);
        resolveEverything(game);

        // Advance naturally to end of combat (blocker survives untouched -- no real
        // damage was dealt since we didn't go through real combat -- so the delayed
        // "still on the battlefield" check should hold) and let the delayed trigger fire.
        playUntilPhase(game, PhaseType.COMBAT_END);
        resolveEverything(game);

        assertTrue(blocker.isInZone(ZoneType.Battlefield), "Blocker should still be on the battlefield");
        assertEquals(p1.getCardsIn(ZoneType.Hand).size(), handBefore + 2, "Surviving the block should have drawn 2 cards");
        assertTrue(!aura.isInZone(ZoneType.Battlefield), "Noch Proderzhatsa should sacrifice itself");
    }

    @Test
    public void holodnayaZemlya_drainsOpponentWhenYourCreatureDies() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        int p2LifeBefore = p2.getLife();

        addCard("Holodnaya Zemlya", p1);
        Card victim = addCard("Grizzly Bears", p1);
        kill(game, victim);

        assertEquals(p2.getLife(), p2LifeBefore - 1, "Opponent should lose 1 life when your creature dies");
    }

    @Test
    public void sglaz_shrinksTargetCreature() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        Card bear = addCard("Grizzly Bears", p2);

        castTargeted(game, p1, "Sglaz", bear, "Swamp", 1);

        assertEquals(bear.getNetPower(), 0, "Sglaz should apply -2/-2");
        assertEquals(bear.getNetToughness(), 0, "Sglaz should apply -2/-2");
    }

    @Test
    public void pominki_eachPlayerSacrificesAndYouGetFood() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        addCard("Grizzly Bears", p1);
        addCard("Runeclaw Bear", p2);

        castFromHand(game, p1, "Pominki", "Swamp", 2);

        assertEquals(p1.getCreaturesInPlay().size(), 0, "p1 should have sacrificed their creature");
        assertEquals(p2.getCreaturesInPlay().size(), 0, "p2 should have sacrificed their creature");
        assertTrue(p1.getCardsIn(ZoneType.Battlefield).anyMatch(c -> c.getType().hasSubtype("Food")),
                "Pominki should have created a Food token for its caster");
    }

    @Test
    public void topkoyeMesto_activatedAbilityMakesTargetDiscardTwo() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        Card topkoye = addCard("Topkoye mesto", p1);
        addCards("Swamp", 2, p1);
        addCardToZone("Plains", p2, ZoneType.Hand);
        addCardToZone("Island", p2, ZoneType.Hand);
        int p2HandBefore = p2.getCardsIn(ZoneType.Hand).size();

        activateAbility(game, p1, topkoye, "{B}{B}: Target player discards two cards", p2);

        assertEquals(p2.getCardsIn(ZoneType.Hand).size(), p2HandBefore - 2,
                "Topkoye mesto should make the target player discard two cards");
    }

    @Test
    public void zakladnayaChertu_returnsCreaturesThenLosesLifeEqualToTheirPower() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card bear1 = addCardToZone("Grizzly Bears", p1, ZoneType.Graveyard); // power 2
        Card bear2 = addCardToZone("Runeclaw Bear", p1, ZoneType.Graveyard); // power 2
        int lifeBefore = p1.getLife();

        addCards("Swamp", 4, p1);
        Card zakladnaya = addCardToZone("Zakladnaya Chertu", p1, ZoneType.Hand);
        SpellAbility sa = zakladnaya.getSpells().get(0);
        sa.setActivatingPlayer(p1);
        sa.getTargets().add(bear1);
        sa.getTargets().add(bear2);
        boolean played = ComputerUtil.playStack(sa, p1, game);
        assertTrue(played, "Zakladnaya Chertu should have been castable");
        game.getStack().resolveStack();
        resolveEverything(game);

        assertTrue(bear1.isInZone(ZoneType.Battlefield), "First targeted creature should return to the battlefield");
        assertTrue(bear2.isInZone(ZoneType.Battlefield), "Second targeted creature should return to the battlefield");

        // Advance THROUGH end of turn (not devModeSet directly onto it -- that just
        // teleports the phase pointer without running the phase-entry trigger checks a
        // natural transition would, so the delayed trigger would never actually fire).
        playUntilPhase(game, PhaseType.END_OF_TURN);
        resolveEverything(game);

        assertEquals(p1.getLife(), lifeBefore - 4,
                "Should lose life equal to the sum of the returned creatures' power (2+2) at end of turn");
    }

    @Test
    public void neSvisti_chosenPlayerDiscardsTwoAfterCastingACreature() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);

        Card nakaz = castFromHand(game, p1, "Ne svisti", "Swamp", 2);
        Player chosen = nakaz.getChosenPlayer();
        assertNotNull(chosen, "Ne svisti should have chosen a player on ETB");

        addCardToZone("Plains", chosen, ZoneType.Hand); // filler for the forced discard
        addCardToZone("Island", chosen, ZoneType.Hand);
        addCards("Forest", 2, chosen); // Grizzly Bears costs {1}{G}
        Card creature = addCardToZone("Grizzly Bears", chosen, ZoneType.Hand);
        int handBeforeCast = chosen.getCardsIn(ZoneType.Hand).size();

        SpellAbility sa = creature.getSpells().get(0);
        sa.setActivatingPlayer(chosen);
        boolean played = ComputerUtil.playStack(sa, chosen, game);
        assertTrue(played, "Chosen player should be able to cast a creature");
        game.getStack().resolveStack();
        resolveEverything(game);

        assertEquals(chosen.getCardsIn(ZoneType.Hand).size(), handBeforeCast - 1 - 2,
                "Chosen player should discard two cards after casting a creature (1 for the cast itself, 2 for the curse)");
        assertTrue(nakaz.isInZone(ZoneType.Graveyard), "Ne svisti should sacrifice itself once triggered");
    }
}
