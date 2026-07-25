
//   <script> ... script utama halaman lu, boleh pake variabel
//              `supabase` dan `currentUser` yang udah disiapin file ini ... </script>
// File ini nge-block eksekusi sampe status login jelas, jadi script
// utama halaman lu aman baru jalan pas udah pasti ada currentUser.


const supabase = window.supabase.createClient(SUPABASE_URL, SUPABASE_ANON_KEY);
let currentUser = null;

async function requireAuth() {
  const { data } = await supabase.auth.getSession();
  if (!data.session) {
    window.location.href = "login.html";
    return null;
  }
  currentUser = data.session.user;
  return currentUser;
}

async function logout() {
  await supabase.auth.signOut();
  window.location.href = "login.html";
}

// Jalanin pengecekan begitu file ini dimuat
const authReady = requireAuth();