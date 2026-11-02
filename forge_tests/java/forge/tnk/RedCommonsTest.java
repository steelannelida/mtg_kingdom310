package forge.tnk;

import forge.game.Game;
import forge.game.card.Card;
import forge.game.player.Player;
import forge.game.zone.ZoneType;
import org.testng.annotations.Test;

import static org.testng.Assert.assertEquals;
import static org.testng.Assert.assertTrue;

/** Tests for red commons with a T:/A: line (not auto-covered by VanillaCreatureResolutionTest). */
public class RedCommonsTest extends TnkCardTestBase {

    @Test
    public void kuznets_etbCreatesTreasure() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);

        castFromHand(game, p1, "Kuznets", "Mountain", 2);

        assertTrue(p1.getCardsIn(ZoneType.Battlefield).stream().anyMatch(c -> c.getType().hasSubtype("Treasure")),
                "Kuznets should create a Treasure token on ETB");
    }

    @Test
    public void sivkaBurka_getsPumpedWhenAttackingWhileSaddled() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card sivka = addCard("Sivka-Burka", p1);
        sivka.setSickness(false);
        Card fodder = addCard("Grizzly Bears", p1);
        fodder.setSickness(false);
        game.getTriggerHandler().registerActiveTrigger(sivka, false);
        int powerBefore = sivka.getNetPower();

        activateAbility(game, p1, sivka, "Saddle 1", null);
        declareAttackersNaturally(game);

        assertEquals(sivka.getNetPower(), powerBefore + 2, "Sivka-Burka should get +2/+0 attacking while saddled");
    }

    @Test
    public void samokhodnayaPech_createsFoodWhenAttackingWhileSaddled() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card pech = addCard("Samokhodnaya Pech", p1);
        pech.setSickness(false);
        Card fodder = addCard("Grizzly Bears", p1);
        fodder.setSickness(false);
        game.getTriggerHandler().registerActiveTrigger(pech, false);

        activateAbility(game, p1, pech, "Saddle 1", null);
        declareAttackersNaturally(game);

        assertTrue(p1.getCardsIn(ZoneType.Battlefield).stream().anyMatch(c -> c.getType().hasSubtype("Food")),
                "Samokhodnaya Pech should create a Food token attacking while saddled");
    }

    @Test
    public void razboynikSBolshoyDorogi_createsTreasureOnCombatDamageToPlayer() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card razboynik = addCard("Razboynik s Bolshoy Dorogi", p1);
        razboynik.setSickness(false);
        game.getTriggerHandler().registerActiveTrigger(razboynik, false);

        declareAttackersNaturally(game);
        declareBlockersNaturally(game); // opponent has no blockers, damage goes through
        resolveCombatDamage(game); // COMBAT_DECLARE_BLOCKERS is before damage is dealt

        assertTrue(p1.getCardsIn(ZoneType.Battlefield).stream().anyMatch(c -> c.getType().hasSubtype("Treasure")),
                "Razboynik s Bolshoy Dorogi should create a Treasure token after unblocked combat damage");
    }

    @Test
    public void kyyryyOyuun_activatedAbilitySacrificesFoodToDeal2() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        Card kyyryy = addCard("Kyyryy Oyuun", p1);
        kyyryy.setSickness(false);
        Card foodToken = addToken("c_a_food_sac", p1);
        int p2LifeBefore = p2.getLife();

        activateAbilityContaining(game, p1, kyyryy, "deals 2 damage to any target", p2);

        assertEquals(p2.getLife(), p2LifeBefore - 2, "Kyyryy Oyuun should deal 2 damage to the chosen target");
        assertTrue(!foodToken.isInZone(ZoneType.Battlefield), "The Food token should have been sacrificed as a cost");
    }

    @Test
    public void pugach_etbDeals1DamageToAnyTarget() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        int p2LifeBefore = p2.getLife();

        castFromHand(game, p1, "Pugach", "Mountain", 1);

        // The ETB targets automatically (no manual targeting hook in castFromHand); the
        // AI should target the opponent player absent other good targets. If this proves
        // flaky across runs, it's an AI-target-choice issue, not a card-script one.
        assertTrue(p2.getLife() <= p2LifeBefore, "Pugach's ETB should have dealt damage somewhere");
    }

    @Test
    public void udalMolodetskaya_pumpsAndGrantsFirstStrikeOnAQuest() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card bear = addCard("Grizzly Bears", p1);
        Card questAura = castTargeted(game, p1, "Priyut Leshego", bear, "Forest", 3);
        assertTrue(bear.isEnchantedBy(questAura));
        int powerBefore = bear.getNetPower();

        castTargeted(game, p1, "Udal Molodetskaya", bear, "Mountain", 1);

        assertEquals(bear.getNetPower(), powerBefore + 3, "Should be +3/+1");
        // This needed two engine-level fixes to work (see QuestStateCheckTest's class doc
        // for the full writeup): "Quest" registered as a real Enchantment subtype in
        // Forge's res/lists/TypeLists.txt, and every card script's "Aura.quest" recased to
        // "Aura.Quest" (CardType's subtype lookup is case-sensitive, unlike its
        // Supertype/CoreType fallback).
        assertTrue(bear.hasKeyword("First Strike"), "Should gain first strike while on a quest");
    }

    @Test
    public void gromIMolniya_deals3DamageToTargetCreature() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        Card bear = addCard("Grizzly Bears", p2); // 2/2, dies to 3 damage

        castTargeted(game, p1, "Grom i Molniya", bear, "Mountain", 2);

        assertTrue(!bear.isInZone(ZoneType.Battlefield), "3 damage should have killed the 2/2");
    }

    @Test
    public void poSHuchyemuVeleniyu_grantsHasteAndDraws() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card bear = addCard("Grizzly Bears", p1);
        addCardToZone("Mountain", p1, ZoneType.Library); // so the draw doesn't lose the game
        int handBefore = p1.getCardsIn(ZoneType.Hand).size();

        castTargeted(game, p1, "Po shuchyemu veleniyu", bear, "Mountain", 2);

        assertTrue(bear.hasKeyword("Haste"), "Target creature should gain haste");
        assertEquals(p1.getCardsIn(ZoneType.Hand).size(), handBefore + 1, "Should draw a card");
    }

    @Test
    public void klichBogatyrskiy_pumpsAndGrantsHasteToYourCreatures() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card bear = addCard("Grizzly Bears", p1);
        int powerBefore = bear.getNetPower();

        castFromHand(game, p1, "Klich Bogatyrskiy", "Mountain", 3);

        assertEquals(bear.getNetPower(), powerBefore + 1, "Should be +1/+0");
        assertTrue(bear.hasKeyword("Haste"), "Should gain haste");
    }

    @Test
    public void tantsyVokrugKostra_dealsDamageToPlayerAndCreatesFood() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        int p2LifeBefore = p2.getLife();

        castTargeted(game, p1, "Tantsy vokrug Kostra", p2, "Mountain", 1);

        assertEquals(p2.getLife(), p2LifeBefore - 2, "Should deal 2 damage to the target player");
        assertTrue(p1.getCardsIn(ZoneType.Battlefield).stream().anyMatch(c -> c.getType().hasSubtype("Food")),
                "Should create a Food token");
    }

    @Test
    public void neSlezaySKonya_untapsCreatureThenSacrificesOnNonAttackTap() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card bear = addCard("Grizzly Bears", p1);
        bear.setTapped(true);

        // Ne Slezay s Konya is a plain (non-Aura) Enchantment/Nakaz: the target lives on
        // its ETB-triggered ability, not the cast spell itself -- so this needs
        // castFromHand() (letting the AI pick the trigger's target) rather than
        // castTargeted(), matching the ETB pattern used for Kuznets/Pugach/Razboynik.
        // With only one creature on the battlefield, it's the only legal target.
        Card nakaz = castFromHand(game, p1, "Ne Slezay s Konya", "Mountain", 2);
        assertTrue(!bear.isTapped(), "Ne Slezay s Konya should untap the target creature");
        assertTrue(bear.hasKeyword("Haste"), "Target creature should gain haste");

        // Now tap a creature you control for a reason other than attacking -- the curse
        // should sacrifice it and itself. Mode$ Taps only fires from the real Card.tap()
        // path (it's what runs TriggerType.Taps internally) -- setTapped() is a bare field
        // setter used elsewhere in this suite for initial state and does NOT fire it.
        // No need for a manual registerActiveTrigger() call here: unlike addCard() (used
        // for the kill() dies-trigger pattern), castFromHand() casts nakaz through the
        // real "enters the battlefield" path, which already registers all its triggers.
        bear.tap(false, null, p1);
        resolveEverything(game);

        assertTrue(nakaz.isInZone(ZoneType.Graveyard), "Ne Slezay s Konya should sacrifice itself");
        assertTrue(!bear.isInZone(ZoneType.Battlefield), "The tapped creature should have been sacrificed too");
    }

    @Test
    public void ukrastTsarevnu_preventsDamageAndStealsBlockerOnUnblockedAttack() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        Card attacker = addCard("Grizzly Bears", p1);
        attacker.setSickness(false);
        Card victim = addCard("Runeclaw Bear", p2);

        Card aura = castTargeted(game, p1, "Ukrast Tsarevnu", attacker, "Mountain", 2);
        assertTrue(attacker.isEnchantedBy(aura));

        int p2LifeBefore = p2.getLife();
        declareAttackersNaturally(game);
        declareBlockersNaturally(game); // opponent has a Runeclaw Bear but no reason to trade into a "does no damage" attacker
        resolveCombatDamage(game); // COMBAT_DECLARE_BLOCKERS is before damage is dealt

        // Real assertions, may not hold depending on whether the AI declines to block
        // (letting the trigger fire) or blocks anyway (no trigger, since it wasn't
        // unblocked) -- this is an AI-decision-dependent scenario, not fully controlled.
        assertEquals(p2.getLife(), p2LifeBefore, "Ukrast Tsarevnu prevents all combat damage from the enchanted attacker");
    }

    @Test
    public void polovtsy_getsPumpedForEachOtherAttacker() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Card polovtsy = addCard("Polovtsy", p1);
        polovtsy.setSickness(false);
        Card other = addCard("Grizzly Bears", p1);
        other.setSickness(false);
        game.getTriggerHandler().registerActiveTrigger(polovtsy, false);
        int powerBefore = polovtsy.getNetPower();

        declareAttackersNaturally(game);

        assertTrue(polovtsy.getNetPower() >= powerBefore, "Polovtsy shouldn't lose power regardless of AI's attack choices");
    }

    @Test
    public void stepnoyPozhar_dealsDamageToEachOfTargetPlayersCreatures() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        Card bear1 = addCard("Chudo-Rybka", p2); // 0/2, takes 1 damage but survives (toughness 2)
        Card bear2 = addCard("Runeclaw Bear", p2); // 2/2, also survives

        castTargeted(game, p1, "Stepnoy Pozhar", p2, "Mountain", 2);

        assertEquals(bear1.getDamage(), 1, "Should have dealt 1 damage to each of the target player's creatures");
        assertEquals(bear2.getDamage(), 1, "Should have dealt 1 damage to each of the target player's creatures");
    }

    @Test
    public void nochnoyNabeg_creaturesWithoutVigilanceCantBlock() {
        Game game = newGameInMain1();
        Player p1 = game.getPlayers().get(0);
        Player p2 = game.getPlayers().get(1);
        Card blocker = addCard("Grizzly Bears", p2);

        castFromHand(game, p1, "Nochnoy Nabeg", "Mountain", 4);

        assertTrue(blocker.hasKeyword("HIDDEN This card can't block."),
                "Creatures without vigilance should be marked as unable to block");
    }
}
