"""voyara_common — code partagé entre les microservices Voyara.

Contenu :
- config      : settings communs (JWT, clé interne, CORS)
- security    : hash de mots de passe, tokens JWT, tokens e-mail
- auth        : dépendances FastAPI d'authentification basées sur le JWT (sans DB)
- internal    : protection et appel des endpoints /internal/* entre services
- database    : fabrique engine/session SQLAlchemy
- pagination  : schéma Page[T] + helper de pagination
- exceptions  : handlers d'exceptions FastAPI communs
- logging     : configuration du logging
- limiter     : rate limiter (slowapi) compatible reverse-proxy
"""
