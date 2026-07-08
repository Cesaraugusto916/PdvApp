import os
from database import db_manager
from core import external_patterns

class Recommender:
    def __init__(self, min_confidence=0.3):
        self.min_confidence = min_confidence
        # Load external rules at initialization
        self.external_rules = external_patterns.fetch_external_patterns()
        
    def get_recommendations(self, current_basket):
        """
        Processes the current basket of product IDs and returns up to 3 recommendations.
        current_basket: list of product IDs
        
        Returns a list of dictionaries, where each dict is a product with recommendation metadata:
        {
          "id": "1003",
          "name": "Adesivo Plástico...",
          "category": "Hidráulica",
          "price": 12.50,
          "layers": ["Histórico Local", "Regras Especialistas"],
          "reasons": ["Comprado frequentemente com Cano PVC e Luva PVC", "Necessário para colagem"]
        }
        """
        if not current_basket:
            return []
            
        basket_set = set(current_basket)
        candidates = {}  # prod_id -> { "layers": set(), "reasons": list(), "score": float }

        # --- Layer 1: Local Purchase History (Association / Co-occurrence) ---
        self._evaluate_local_history(basket_set, candidates)

        # --- Layer 2: Category Profiles (Expert Rules / Cross-sell) ---
        self._evaluate_expert_complements(basket_set, candidates)

        # --- Layer 3: External Patterns (Web Rules) ---
        self._evaluate_external_patterns(basket_set, candidates)

        # --- Final Selection & Details Fetching ---
        return self._compile_top_suggestions(basket_set, candidates)

    def _evaluate_local_history(self, basket_set, candidates):
        """Analyzes database sales history for frequent itemset patterns."""
        history = db_manager.get_local_sales_history()
        if not history:
            return
            
        # Find transactions matching subsets of the basket
        # We check full matches first, then pairwise if no matches found
        matching_transactions = []
        for t in history:
            t_set = set(t)
            # If the transaction contains at least one item and we evaluate co-occurrences
            intersection = basket_set.intersection(t_set)
            if intersection:
                matching_transactions.append((t_set, intersection))
                
        if not matching_transactions:
            return
            
        # Count frequency of other items bought alongside the basket items
        co_occurrences = {}
        # We also count support for items in the intersection to calculate confidence
        base_counts = {}
        
        for t_set, intersection in matching_transactions:
            # We treat the intersection as the antecedent
            key = tuple(sorted(intersection))
            base_counts[key] = base_counts.get(key, 0) + 1
            
            for item in t_set:
                if item not in basket_set:
                    co_occurrences[item] = co_occurrences.get(item, {})
                    co_occurrences[item][key] = co_occurrences[item].get(key, 0) + 1

        for item, antecedent_counts in co_occurrences.items():
            for antecedent, freq in antecedent_counts.items():
                confidence = freq / base_counts[antecedent]
                if confidence >= self.min_confidence:
                    # Score is based on confidence and support size
                    score_boost = confidence * (len(antecedent) * 1.5)
                    
                    # Fetch antecedent names for a friendly explanation
                    antecedent_names = []
                    for ant_id in antecedent:
                        prod = db_manager.get_product(ant_id)
                        if prod:
                            antecedent_names.append(prod["name"])
                    
                    ant_str = " + ".join(antecedent_names) if antecedent_names else "itens no carrinho"
                    reason = f"Comprado com {ant_str} ({int(confidence * 100)}% das vezes no histórico)"
                    
                    if item not in candidates:
                        candidates[item] = {"layers": set(), "reasons": [], "score": 0.0}
                    
                    candidates[item]["layers"].add("Histórico Local")
                    candidates[item]["reasons"].append(reason)
                    candidates[item]["score"] += score_boost

    def _evaluate_expert_complements(self, basket_set, candidates):
        """Evaluates predefined SQL expert complements (Category Profiles)."""
        for prod_id in basket_set:
            complements = db_manager.get_complements_for_product(prod_id)
            for comp in complements:
                comp_id = comp["complement_id"]
                if comp_id in basket_set:
                    continue
                    
                reason = f"Complemento recomendado para '{db_manager.get_product(prod_id)['name']}': {comp['reason']}"
                
                if comp_id not in candidates:
                    candidates[comp_id] = {"layers": set(), "reasons": [], "score": 0.0}
                    
                candidates[comp_id]["layers"].add("Perfil de Categoria")
                candidates[comp_id]["reasons"].append(reason)
                # Expert rules get a solid base score boost
                candidates[comp_id]["score"] += 1.2

    def _evaluate_external_patterns(self, basket_set, candidates):
        """Matches current basket against global patterns loaded from the web."""
        if not self.external_rules:
            return
            
        for rule in self.external_rules:
            antecedents = set(rule.get("antecedents", []))
            consequent = rule.get("consequent")
            
            # Check if all antecedents of the rule are in the basket
            if antecedents and antecedents.issubset(basket_set) and consequent not in basket_set:
                confidence = rule.get("confidence", 0.5)
                lift = rule.get("lift", 1.0)
                description = rule.get("description", "Padrão de mercado")
                
                # Rule score combines confidence and lift
                score_boost = confidence * lift * 0.5
                reason = f"Padrão de Mercado: {description} (Confiança: {int(confidence*100)}%, Lift: {lift})"
                
                if consequent not in candidates:
                    candidates[consequent] = {"layers": set(), "reasons": [], "score": 0.0}
                    
                candidates[consequent]["layers"].add("Padrões de Mercado (Web)")
                candidates[consequent]["reasons"].append(reason)
                candidates[consequent]["score"] += score_boost

    def _compile_top_suggestions(self, basket_set, candidates):
        """Ranks candidates, fetches product details, and returns top 3 suggestions."""
        # Sort candidates by score descending
        sorted_candidates = sorted(candidates.items(), key=lambda x: x[1]["score"], reverse=True)
        
        recommendations = []
        for prod_id, meta in sorted_candidates:
            if len(recommendations) >= 3:
                break
                
            prod_details = db_manager.get_product(prod_id)
            if prod_details:
                recommendations.append({
                    "id": prod_id,
                    "name": prod_details["name"],
                    "category": prod_details["category"],
                    "price": prod_details["price"],
                    "layers": list(meta["layers"]),
                    "reasons": meta["reasons"],
                    "score": round(meta["score"], 2)
                })
                
        return recommendations

if __name__ == "__main__":
    # Test recommender logic
    db_manager.init_db()
    recommender = Recommender()
    
    # Test Case 1: Pipe and Sleeve (Hidráulica)
    print("--- Teste 1: Cano PVC (1001) + Luva PVC (1002) ---")
    recs = recommender.get_recommendations(["1001", "1002"])
    for r in recs:
        print(f"Sugestão: {r['name']} ({r['category']}) - R$ {r['price']:.2f}")
        print(f"  Camadas: {', '.join(r['layers'])}")
        print("  Motivos:")
        for reason in r["reasons"]:
            print(f"    - {reason}")
            
    # Test Case 2: Toilet (3001)
    print("\n--- Teste 2: Bacia Sanitária (3001) ---")
    recs = recommender.get_recommendations(["3001"])
    for r in recs:
        print(f"Sugestão: {r['name']} - R$ {r['price']:.2f}")
        print(f"  Camadas: {', '.join(r['layers'])}")
        print("  Motivos:")
        for reason in r["reasons"]:
            print(f"    - {reason}")
