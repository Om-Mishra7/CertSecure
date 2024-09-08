module 0xbea350440901118a6a5c369ace28249e19cb4d24affa1379b58a2ae1954fb9d2::certsecure {
    use aptos_std::table::{Table, new, upsert, contains, borrow}; 
    use std::string::String; 
    use aptos_std::timestamp::now_seconds; 

    struct Certificate has copy, drop, store {
        id: u64,
        holder_name: String,
        issuer_name: String,
        issued_on: u64,
        valid_until: u64,
    }

    struct CertificateList has key, store {
        certificates: Table<u64, Certificate>, 
        counter: u64, 
    }

    const E_CERTIFICATE_DOESNT_EXIST: u64 = 1;

    public fun initialize(owner: &signer) {
        let cert_list = CertificateList {
            certificates: new(),
            counter: 0,
        };
        move_to(owner, cert_list);
    }

    public fun issue_certificate(
        owner: &mut CertificateList, 
        holder_name: String, 
        issuer_name: String, 
        valid_until: u64
    ) {
        let id = owner.counter;
        let issued_on = now_seconds();
        let new_certificate = Certificate {
            id,
            holder_name,
            issuer_name,
            issued_on,
            valid_until,
        };
        upsert(&mut owner.certificates, id, new_certificate);
        owner.counter = owner.counter + 1;
    }

    public fun certificate_exists(cert_list: &CertificateList, cert_id: u64): bool {
        contains(&cert_list.certificates, cert_id)
    }

    public fun get_certificate(cert_list: &CertificateList, cert_id: u64): &Certificate {
        assert!(contains(&cert_list.certificates, cert_id), E_CERTIFICATE_DOESNT_EXIST);
        borrow(&cert_list.certificates, cert_id)
    }
}
