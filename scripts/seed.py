from app.models.user import User 
from app.models.tenant import Tenant
from app.core.database import SessionLocal
db = SessionLocal()

try:
    
    tenant = Tenant(name="Palms Holdings")
    db.add(tenant)
    db.flush()  # Flush to get the tenant ID before committing
    user = User(email = "jane.doe@gmail.com", hashed_password = "hashedpassword", tenant_id = tenant.id, role = "manager")
    db.add(user)
    db.flush()  # Flush to get the user ID before committing
    print(f"Tenant created: {tenant.name} with ID: {tenant.id}")
    print(f"User created: {user.email} with ID: {user.id}, Tenant ID: {user.tenant_id}, and role: {user.role}")
    db.commit()
    
except Exception as e:
    
    db.rollback()
    print(f"An error occurred: {e}")
    
finally:
    
    db.close()