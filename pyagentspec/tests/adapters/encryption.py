# Copyright © 2025 Oracle and/or its affiliates.
#
# This software is under the Apache License 2.0
# (LICENSE-APACHE or http://www.apache.org/licenses/LICENSE-2.0) or Universal Permissive License
# (UPL) 1.0 (LICENSE-UPL or https://oss.oracle.com/licenses/upl), at your option.

import datetime as dt
import ipaddress
import logging
import os

from cryptography import x509
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import rsa
from cryptography.hazmat.primitives.serialization import (
    BestAvailableEncryption,
    Encoding,
    NoEncryption,
    PrivateFormat,
)
from cryptography.x509 import Name, NameAttribute
from cryptography.x509.oid import ExtendedKeyUsageOID, NameOID

logger = logging.getLogger(__name__)


def now_utc():
    return dt.datetime.now(dt.timezone.utc)


def write_pem(path: str, data: bytes):
    with open(path, "wb") as f:
        f.write(data)
    logger.info(f"Wrote {path}")


def save_private_key(path: str, key: rsa.RSAPrivateKey, password: bytes | None = None):
    if password:
        enc = BestAvailableEncryption(password)
    else:
        enc = NoEncryption()
    pem = key.private_bytes(
        encoding=Encoding.PEM,
        format=PrivateFormat.TraditionalOpenSSL,
        encryption_algorithm=enc,
    )
    write_pem(path, pem)


def save_cert(path: str, cert: x509.Certificate):
    write_pem(path, cert.public_bytes(Encoding.PEM))


def save_csr(path: str, csr: x509.CertificateSigningRequest):
    write_pem(path, csr.public_bytes(Encoding.PEM))


def create_root_ca(common_name: str = "TestRootCA", days=3650, tmpdir: str = ""):
    ca_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    save_private_key(os.path.join(str(tmpdir), "rootCA.key"), ca_key)

    # Subject/Issuer (self-signed)
    name = Name([NameAttribute(NameOID.COMMON_NAME, common_name)])
    builder = (
        x509.CertificateBuilder()
        .subject_name(name)
        .issuer_name(name)
        .public_key(ca_key.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now_utc() - dt.timedelta(minutes=1))
        .not_valid_after(now_utc() + dt.timedelta(days=days))
        .add_extension(
            x509.BasicConstraints(ca=True, path_length=0),
            critical=True,
        )
        .add_extension(
            x509.KeyUsage(
                digital_signature=False,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=True,
                crl_sign=True,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(ca_key.public_key()),
            critical=False,
        )
    )

    ca_cert = builder.sign(private_key=ca_key, algorithm=hashes.SHA256())
    ca_cert_path = os.path.join(str(tmpdir), "rootCA.pem")
    save_cert(ca_cert_path, ca_cert)
    return ca_key, ca_cert, ca_cert_path


def create_server_key_and_csr(cn: str = "localhost", tmpdir: str = ""):
    server_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    server_key_path = os.path.join(str(tmpdir), "server.key")
    save_private_key(server_key_path, server_key)

    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(Name([NameAttribute(NameOID.COMMON_NAME, cn)]))
        .sign(server_key, hashes.SHA256())
    )
    save_csr(os.path.join(str(tmpdir), "server.csr"), csr)
    return server_key, csr, server_key_path


def issue_server_cert(
    ca_key: rsa.RSAPrivateKey,
    ca_cert: x509.Certificate,
    csr: x509.CertificateSigningRequest,
    days: int = 365,
    tmpdir: str = "",
):
    san = x509.SubjectAlternativeName(
        [
            x509.DNSName("localhost"),
            x509.IPAddress(ipaddress.IPv4Address("127.0.0.1")),
        ]
    )

    builder = (
        x509.CertificateBuilder()
        .subject_name(csr.subject)
        .issuer_name(ca_cert.subject)
        .public_key(csr.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now_utc() - dt.timedelta(minutes=1))
        .not_valid_after(now_utc() + dt.timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=True,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.SERVER_AUTH]),
            critical=False,
        )
        .add_extension(san, critical=False)
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(csr.public_key()),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        )
    )

    cert = builder.sign(private_key=ca_key, algorithm=hashes.SHA256())
    server_cert_path = os.path.join(str(tmpdir), "server.crt")
    save_cert(server_cert_path, cert)
    return cert, server_cert_path


def create_client_key_and_csr(cn: str = "mtls-client", tmpdir: str = ""):
    client_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    client_key_path = os.path.join(str(tmpdir), "client.key")
    save_private_key(client_key_path, client_key)

    csr = (
        x509.CertificateSigningRequestBuilder()
        .subject_name(Name([NameAttribute(NameOID.COMMON_NAME, cn)]))
        .sign(client_key, hashes.SHA256())
    )
    save_csr(os.path.join(str(tmpdir), "client.csr"), csr)
    return client_key, csr, client_key_path


def issue_client_cert(
    ca_key: rsa.RSAPrivateKey,
    ca_cert: x509.Certificate,
    csr: x509.CertificateSigningRequest,
    days: int = 365,
    tmpdir: str = "",
):
    builder = (
        x509.CertificateBuilder()
        .subject_name(csr.subject)
        .issuer_name(ca_cert.subject)
        .public_key(csr.public_key())
        .serial_number(x509.random_serial_number())
        .not_valid_before(now_utc() - dt.timedelta(minutes=1))
        .not_valid_after(now_utc() + dt.timedelta(days=days))
        .add_extension(x509.BasicConstraints(ca=False, path_length=None), critical=True)
        .add_extension(
            x509.KeyUsage(
                digital_signature=True,
                content_commitment=False,
                key_encipherment=False,
                data_encipherment=False,
                key_agreement=False,
                key_cert_sign=False,
                crl_sign=False,
                encipher_only=False,
                decipher_only=False,
            ),
            critical=True,
        )
        .add_extension(
            x509.ExtendedKeyUsage([ExtendedKeyUsageOID.CLIENT_AUTH]),
            critical=False,
        )
        .add_extension(
            x509.SubjectKeyIdentifier.from_public_key(csr.public_key()),
            critical=False,
        )
        .add_extension(
            x509.AuthorityKeyIdentifier.from_issuer_public_key(ca_key.public_key()),
            critical=False,
        )
    )

    cert = builder.sign(private_key=ca_key, algorithm=hashes.SHA256())
    client_cert_path = os.path.join(str(tmpdir), "client.crt")
    save_cert(client_cert_path, cert)
    return cert, client_cert_path


def print_quick_checks(server_cert: x509.Certificate, client_cert: x509.Certificate):
    # Server SANs
    try:
        san = server_cert.extensions.get_extension_for_class(x509.SubjectAlternativeName).value
        entries = []
        for d in san:
            if isinstance(d, x509.DNSName):
                entries.append(f"DNS:{d.value}")
            elif isinstance(d, x509.IPAddress):
                entries.append(f"IP:{d.value.exploded}")
        logger.info("Server SAN ->", ", ".join(entries))
    except x509.ExtensionNotFound:
        logger.info("Server SAN -> (none)")

    # Client EKU
    try:
        eku = client_cert.extensions.get_extension_for_class(x509.ExtendedKeyUsage).value
        eku_names = []
        for oid in eku:
            if oid == ExtendedKeyUsageOID.CLIENT_AUTH:
                eku_names.append("TLS Web Client Authentication")
            elif oid == ExtendedKeyUsageOID.SERVER_AUTH:
                eku_names.append("TLS Web Server Authentication")
            else:
                eku_names.append(oid.dotted_string)
        logger.info("Client EKU ->", ", ".join(eku_names))
    except x509.ExtensionNotFound:
        logger.info("Client EKU -> (none)")


if __name__ == "__main__":
    # 1. Root CA
    ca_key, ca_cert, ca_cert_path = create_root_ca(common_name="TestRootCA", days=3650)
    # 2. Server key + CSR
    server_key, server_csr, server_key_path = create_server_key_and_csr(cn="localhost")
    # 3. Issue server cert (SAN: localhost + 127.0.0.1)
    server_cert, server_cert_path = issue_server_cert(ca_key, ca_cert, server_csr, days=365)
    # 4. Client key + CSR
    client_key, client_csr, client_key_path = create_client_key_and_csr(cn="mtls-client")
    # 5. Issue client cert (EKU: clientAuth)
    client_cert, client_cert_path = issue_client_cert(ca_key, ca_cert, client_csr, days=365)
    # 6. Quick checks
    print_quick_checks(server_cert, client_cert)
