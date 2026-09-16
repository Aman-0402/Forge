import { useAuth } from "../auth/AuthContext";

export default function MePage() {
  const { user } = useAuth();
  return (
    <>
      <h1>My profile</h1>
      <pre>{JSON.stringify(user, null, 2)}</pre>
    </>
  );
}
