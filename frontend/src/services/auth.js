import { AuthenticationDetails, CognitoUser, CognitoUserPool } from "amazon-cognito-identity-js";

let pool;
export function initAuth(cfg) {
  pool = new CognitoUserPool({ UserPoolId: cfg.userPoolId, ClientId: cfg.userPoolClientId });
}

export function currentSession() {
  return new Promise((resolve) => {
    const user = pool?.getCurrentUser();
    if (!user) return resolve(null);
    user.getSession((err, session) => resolve(err || !session?.isValid() ? null : { user, session }));
  });
}

export async function idToken() {
  const s = await currentSession();
  return s ? s.session.getIdToken().getJwtToken() : null;
}

export function signIn(email, password, newPassword) {
  return new Promise((resolve, reject) => {
    const user = new CognitoUser({ Username: email, Pool: pool });
    user.authenticateUser(new AuthenticationDetails({ Username: email, Password: password }), {
      onSuccess: (session) => resolve({ user, session }),
      onFailure: reject,
      newPasswordRequired: () => {
        if (!newPassword) return reject({ code: "NewPasswordRequired", message: "Set a new password to finish first sign-in." });
        user.completeNewPasswordChallenge(newPassword, {}, {
          onSuccess: (session) => resolve({ user, session }),
          onFailure: reject,
        });
      },
    });
  });
}

export function signOut() {
  pool?.getCurrentUser()?.signOut();
}
