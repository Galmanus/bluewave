interface TeamMember {
  user_id: string;
  full_name: string;
  uploads: number;
  approvals: number;
}

export default function TeamTable({ members }: { members: TeamMember[] }) {
  if (!members.length) {
    return <p className="text-gray-500 text-sm">No team activity in this period.</p>;
  }

  return (
    <div className="bg-white dark:bg-gray-900 border dark:border-gray-800 rounded-xl overflow-hidden">
      <table className="w-full text-sm">
        <thead className="bg-gray-50 dark:bg-gray-800 text-gray-500">
          <tr>
            <th className="text-left p-3">Team Member</th>
            <th className="text-right p-3">Uploads</th>
            <th className="text-right p-3">Approved</th>
          </tr>
        </thead>
        <tbody>
          {members.map((m) => (
            <tr key={m.user_id} className="border-t dark:border-gray-800">
              <td className="p-3 font-medium">{m.full_name}</td>
              <td className="p-3 text-right">{m.uploads}</td>
              <td className="p-3 text-right">{m.approvals}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}
