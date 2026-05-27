import React, { useEffect, useState } from 'react';
import api from '../../api/client';
import { useSelector } from 'react-redux';

const CommentsPanel = ({ row, source }) => {
    const [comments, setComments] = useState([]);
    const [newComment, setNewComment] = useState('');
    const [isFinding, setIsFinding] = useState(false);
    const { user } = useSelector((state) => state.auth);

    const fetchComments = () => {
        api.get(`ingestion/rows/${source}/${row.id}/comments/`)
            .then(res => setComments(res.data.results || res.data))
            .catch(console.error);
    };

    useEffect(() => {
        fetchComments();
    }, [row]);

    const handleSubmit = async (e) => {
        e.preventDefault();
        if (!newComment.trim()) return;
        try {
            await api.post(`ingestion/rows/${source}/${row.id}/comments/`, {
                body: newComment,
                is_finding: isFinding
            });
            setNewComment('');
            setIsFinding(false);
            fetchComments();
        } catch (err) {
            console.error(err);
            alert("Error adding comment");
        }
    };

    const handleResolve = async (commentId) => {
        try {
            await api.patch(`ingestion/rows/comments/${commentId}/resolve/`);
            fetchComments();
        } catch (err) {
            console.error(err);
            alert("Error resolving finding");
        }
    };

    return (
        <div className="flex flex-col h-full">
            <div className="flex-1 space-y-4 mb-4">
                {(!comments || comments.length === 0) ? (
                    <p className="text-sm text-gray-500">No comments yet.</p>
                ) : (
                    comments.map(c => (
                        <div key={c.id} className={`p-3 rounded-lg text-sm border ${c.is_finding ? 'bg-red-50 border-red-200' : 'bg-gray-50 border-gray-200'}`}>
                            <div className="flex justify-between text-xs text-gray-500 mb-2">
                                <span className="font-medium text-gray-700">
                                    {c.author_details?.first_name} {c.author_details?.last_name} ({c.role_at_time})
                                </span>
                                <span>{new Date(c.created_at).toLocaleString()}</span>
                            </div>
                            <p className="text-gray-800">{c.body}</p>
                            {c.is_finding && (
                                <div className="mt-2 text-xs flex justify-between items-center border-t pt-2 border-red-200">
                                    {c.resolved ? (
                                        <span className="text-green-600 font-medium">Resolved by {c.resolved_by_details?.first_name}</span>
                                    ) : (
                                        <>
                                            <span className="text-red-600 font-medium">Unresolved Finding</span>
                                            {(user?.role === 'ANALYST' || user?.role === 'ADMIN') && (
                                                <button onClick={() => handleResolve(c.id)} className="text-blue-600 hover:underline">
                                                    Mark Resolved
                                                </button>
                                            )}
                                        </>
                                    )}
                                </div>
                            )}
                        </div>
                    ))
                )}
            </div>
            
            <form onSubmit={handleSubmit} className="border-t pt-4">
                <textarea
                    value={newComment}
                    onChange={e => setNewComment(e.target.value)}
                    placeholder="Add a comment or finding..."
                    className="w-full border rounded p-2 text-sm focus:ring focus:border-blue-300"
                    rows="3"
                />
                <div className="flex justify-between items-center mt-2">
                    <label className="text-sm flex items-center gap-2">
                        <input type="checkbox" checked={isFinding} onChange={e => setIsFinding(e.target.checked)} disabled={user?.role !== 'AUDITOR' && user?.role !== 'ADMIN'} />
                        Mark as Formal Finding (Auditor only)
                    </label>
                    <button type="submit" className="bg-blue-600 text-white px-4 py-2 rounded text-sm hover:bg-blue-700">
                        Post
                    </button>
                </div>
            </form>
        </div>
    );
};

export default CommentsPanel;
